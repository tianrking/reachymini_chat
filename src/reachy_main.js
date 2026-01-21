
import * as THREE from 'three';
import { GUI } from '../node_modules/three/examples/jsm/libs/lil-gui.module.min.js';
import { OrbitControls } from '../node_modules/three/examples/jsm/controls/OrbitControls.js';
import { DragStateManager } from './utils/DragStateManager.js';
import { setupGUI, loadSceneFromURL, drawTendonsAndFlex, getPosition, getQuaternion, toMujocoPos, standardNormal } from './mujocoUtils.js';
import load_mujoco from '../node_modules/mujoco-js/dist/mujoco_wasm.js';

// Load the MuJoCo Module
const mujoco = await load_mujoco();

// Set up Emscripten's Virtual File System
var initialScene = "reachy_mini/reachy_mini.xml"; // Pointing to our new main file
mujoco.FS.mkdir('/working');
mujoco.FS.mount(mujoco.MEMFS, { root: '.' }, '/working');

// Check if scene.xml exists, if so we might want to use that, but let's stick to reachy_mini.xml or scene.xml
// The user asked to load "reachy_mini.xml" AND mentioned "complete mjcf".
// Looking at the file list, `scene.xml` includes `reachy_mini.xml`.
// Let's use `reachy_mini/scene.xml` as the entry point if possible, as it likely sets up the environment.
// However, the user specifically mentioned `reachy_mini.xml` in the prompt "loading the complete mjcf".
// `scene.xml` adds lights and floor, which is good for a demo. I'll use `reachy_mini/scene.xml`.
initialScene = "reachy_mini/scene.xml";

export class MuJoCoDemo {

    constructor() {
        this.mujoco = mujoco;

        // Load in the state from XML
        this.model = null;
        this.data = null;

        // Define Random State Variables
        this.params = { scene: initialScene, paused: false, help: false, ctrlnoiserate: 0.0, ctrlnoisestd: 0.0, keyframeNumber: 0 };
        this.mujoco_time = 0.0;
        this.bodies = {}, this.lights = {};
        this.tmpVec = new THREE.Vector3();
        this.tmpQuat = new THREE.Quaternion();
        this.updateGUICallbacks = [];

        // MQTT Flag to prevent feedback loops
        this.isReceivingMqtt = false;

        this.container = document.createElement('div');
        document.body.appendChild(this.container);

        this.scene = new THREE.Scene();
        this.scene.name = 'scene';

        this.camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.001, 100);
        this.camera.name = 'PerspectiveCamera';
        // Optimized Camera Position for Reachy Mini (closer and centered)
        this.camera.position.set(0.5, 0.4, 0.8);
        this.scene.add(this.camera);

        this.scene.background = new THREE.Color(0.15, 0.25, 0.35);
        this.scene.fog = new THREE.Fog(this.scene.background, 15, 25.5);

        this.ambientLight = new THREE.AmbientLight(0xffffff, 0.2 * 3.14); // Slightly brighter ambient
        this.ambientLight.name = 'AmbientLight';
        this.scene.add(this.ambientLight);

        this.spotlight = new THREE.SpotLight();
        this.spotlight.angle = 0.8; // Focussed spotlight
        this.spotlight.distance = 100;
        this.spotlight.penumbra = 0.5;
        this.spotlight.castShadow = true;
        this.spotlight.intensity = this.spotlight.intensity * 3.14 * 5.0; // Balanced Intensity
        this.spotlight.shadow.mapSize.width = 2048; // Higher res shadows
        this.spotlight.shadow.mapSize.height = 2048;
        this.spotlight.shadow.camera.near = 0.1;
        this.spotlight.shadow.camera.far = 10;
        this.spotlight.position.set(1, 2, 1);
        const targetObject = new THREE.Object3D();
        this.scene.add(targetObject);
        this.spotlight.target = targetObject;
        targetObject.position.set(0, 0.2, 0); // Aim at robot center
        this.scene.add(this.spotlight);

        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setPixelRatio(window.devicePixelRatio); // Use device pixel ratio for sharper image
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.shadowMap.enabled = true;
        this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        THREE.ColorManagement.enabled = false;
        this.renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
        this.renderer.useLegacyLights = true;

        this.renderer.setAnimationLoop(this.render.bind(this));

        this.container.appendChild(this.renderer.domElement);

        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.target.set(0, 0.2, 0); // Orbit around robot center
        this.controls.panSpeed = 2;
        this.controls.zoomSpeed = 1;
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.10;
        this.controls.screenSpacePanning = true;
        this.controls.update();

        window.addEventListener('resize', this.onWindowResize.bind(this));

        // Initialize the Drag State Manager.
        this.dragStateManager = new DragStateManager(this.scene, this.renderer, this.camera, this.container.parentElement, this.controls);
    }

    async init() {
        // Download the Reachy assets to MuJoCo's virtual file system
        await downloadReachyAssets(mujoco);

        // Initialize the three.js Scene using the .xml Model in initialScene
        [this.model, this.data, this.bodies, this.lights] =
            await loadSceneFromURL(mujoco, initialScene, this);

        this.gui = new GUI();
        setupGUI(this);

        // Hook into GUI for MQTT Sync
        this.hookActuatorGUI();
        this.updateGUICallbacks.push(() => {
            this.hookActuatorGUI();
        });

        // Remove "Example Scene" dropdown to restrict to Reachy Mini
        const sceneCtrl = this.gui.controllers.find(c => c._name === 'Example Scene');
        if (sceneCtrl) {
            sceneCtrl.destroy();
        }

        // --- MQTT Remote Control Setup ---
        this.mqttClient = null;
        this.mqttParams = {
            robotId: "reachy_1",
            brokerUrl: 'wss://broker.emqx.io:8084/mqtt',
            status: "Disconnected",
            connect: async () => {
                if (this.mqttClient && this.mqttClient.connected) {
                    this.mqttClient.end();
                    this.mqttParams.status = "Disconnected";
                    connectCtrl.name("Connect MQTT");
                    return;
                }

                this.mqttParams.status = "Connecting...";

                try {
                    const mqttModule = await import('mqtt');
                    const mqtt = mqttModule.default || mqttModule;

                    console.log(`Connecting to ${this.mqttParams.brokerUrl} as ${this.mqttParams.robotId}...`);

                    if (typeof mqtt.connect !== 'function') {
                        throw new Error(`mqtt.connect is not a function. Keys: ${Object.keys(mqtt)}`);
                    }

                    this.mqttClient = mqtt.connect(this.mqttParams.brokerUrl);

                    this.mqttClient.on('connect', () => {
                        console.log("MQTT Connected!");
                        this.mqttParams.status = "Connected";
                        connectCtrl.name("Disconnect MQTT");

                        // Subscribe to control topic
                        const topic = `reachy/${this.mqttParams.robotId}/cmd`;
                        this.mqttClient.subscribe(topic, (err) => {
                            if (!err) {
                                console.log(`Subscribed to ${topic}`);
                            }
                        });
                    });

                    this.mqttClient.on('message', (topic, message) => {
                        // Handle control messages
                        try {
                            const payload = JSON.parse(message.toString());
                            // Sync External -> Internal
                            if (payload.ctrl && this.data) {
                                this.isReceivingMqtt = true; // Prevent feedback loop

                                const actFolder = this.gui.folders.find(f => f._title === "Actuators");
                                const controllers = actFolder ? actFolder.controllers : [];

                                for (let i = 0; i < Math.min(payload.ctrl.length, this.data.ctrl.length); i++) {
                                    // Update Physics
                                    this.data.ctrl[i] = payload.ctrl[i];

                                    // Update GUI (if matched)
                                    // Assuming 1:1 mapping between ctrl index and controller index
                                    if (i < controllers.length) {
                                        // check if value effectively changed to avoid redundant updates?
                                        // setValue triggers onChange, which we have caught.
                                        controllers[i].setValue(payload.ctrl[i]);
                                    }
                                }
                                this.isReceivingMqtt = false;
                            }
                        } catch (e) {
                            console.error("MQTT Message Error:", e);
                            this.isReceivingMqtt = false;
                        }
                    });

                    this.mqttClient.on('error', (err) => {
                        console.error("MQTT Error:", err);
                        this.mqttParams.status = "Error";
                    });

                } catch (e) {
                    console.error("Failed to load MQTT:", e);
                    this.mqttParams.status = "Load Failed";
                }
            }
        };

        const mqttFolder = this.gui.addFolder("Remote Control (MQTT)");
        mqttFolder.add(this.mqttParams, 'robotId').name("Robot ID");
        mqttFolder.add(this.mqttParams, 'brokerUrl').name("Broker URL");
        mqttFolder.add(this.mqttParams, 'status').name("Status").listen().disable();
        const connectCtrl = mqttFolder.add(this.mqttParams, 'connect').name("Connect MQTT");
        mqttFolder.open();


        // Custom GUI Organization for Reachy
        const actuatorsFolder = this.gui.folders.find(f => f._title === "Actuators");
        if (actuatorsFolder) {
            actuatorsFolder.open();
        }
    }

    hookActuatorGUI() {
        const actFolder = this.gui.folders.find(f => f._title === "Actuators");
        if (!actFolder) return;

        actFolder.controllers.forEach((controller) => {
            // Save original onChange if needed, but lil-gui overwrites it.
            // But we know mujocoUtils sets it to update data.ctrl.
            // We must PRESERVE that behavior.

            // lil-gui stores the callback in `_onChange`.
            const originalOnChange = controller._onChange;

            controller.onChange((value) => {
                // 1. Run original physics update
                if (originalOnChange) {
                    originalOnChange.call(controller, value);
                }

                // 2. Publish Sync (Internal -> External)
                // Only if NOT currently applying an external update
                if (!this.isReceivingMqtt && this.mqttClient && this.mqttClient.connected) {
                    this.publishCommand();
                }
            });
        });
    }

    publishCommand() {
        if (!this.data) return;
        const cmd = {
            time: this.data.time,
            ctrl: Array.from(this.data.ctrl) // Send full control array
        };
        // Publish to CMD topic? Or separate Manual topic?
        // User requested "sync". If we publish to CMD, other listeners will receive it.
        // This allows controlling other clients.
        const topic = `reachy/${this.mqttParams.robotId}/cmd`;
        this.mqttClient.publish(topic, JSON.stringify(cmd));
    }

    onWindowResize() {
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }

    render(timeMS) {
        this.controls.update();

        // If model not loaded yet, skip
        if (!this.model) return;

        if (!this.params["paused"]) {
            let timestep = this.model.opt.timestep;
            if (timeMS - this.mujoco_time > 35.0) { this.mujoco_time = timeMS; }
            while (this.mujoco_time < timeMS) {

                // Jitter the control state with gaussian random noise
                if (this.params["ctrlnoisestd"] > 0.0) {
                    let rate = Math.exp(-timestep / Math.max(1e-10, this.params["ctrlnoiserate"]));
                    let scale = this.params["ctrlnoisestd"] * Math.sqrt(1 - rate * rate);
                    let currentCtrl = this.data.ctrl;
                    for (let i = 0; i < currentCtrl.length; i++) {
                        currentCtrl[i] = rate * currentCtrl[i] + scale * standardNormal();
                        this.params["Actuator " + i] = currentCtrl[i];
                    }
                }

                // Clear old perturbations, apply new ones.
                for (let i = 0; i < this.data.qfrc_applied.length; i++) { this.data.qfrc_applied[i] = 0.0; }
                let dragged = this.dragStateManager.physicsObject;
                if (dragged && dragged.bodyID) {
                    for (let b = 0; b < this.model.nbody; b++) {
                        if (this.bodies[b]) {
                            getPosition(this.data.xpos, b, this.bodies[b].position);
                            getQuaternion(this.data.xquat, b, this.bodies[b].quaternion);
                            this.bodies[b].updateWorldMatrix();
                        }
                    }
                    let bodyID = dragged.bodyID;
                    this.dragStateManager.update(); // Update the world-space force origin
                    let force = toMujocoPos(this.dragStateManager.currentWorld.clone().sub(this.dragStateManager.worldHit).multiplyScalar(this.model.body_mass[bodyID] * 250));
                    let point = toMujocoPos(this.dragStateManager.worldHit.clone());
                    mujoco.mj_applyFT(this.model, this.data, [force.x, force.y, force.z], [0, 0, 0], [point.x, point.y, point.z], bodyID, this.data.qfrc_applied);
                }

                mujoco.mj_step(this.model, this.data);

                this.mujoco_time += timestep * 1000.0;
            }

        } else if (this.params["paused"]) {
            this.dragStateManager.update(); // Update the world-space force origin
            let dragged = this.dragStateManager.physicsObject;
            if (dragged && dragged.bodyID) {
                let b = dragged.bodyID;
                getPosition(this.data.xpos, b, this.tmpVec, false); // Get raw coordinate from MuJoCo
                getQuaternion(this.data.xquat, b, this.tmpQuat, false); // Get raw coordinate from MuJoCo

                let offset = toMujocoPos(this.dragStateManager.currentWorld.clone()
                    .sub(this.dragStateManager.worldHit).multiplyScalar(0.3));
                if (this.model.body_mocapid[b] >= 0) {
                    // Set the root body's mocap position...
                    console.log("Trying to move mocap body", b);
                    let addr = this.model.body_mocapid[b] * 3;
                    let pos = this.data.mocap_pos;
                    pos[addr + 0] += offset.x;
                    pos[addr + 1] += offset.y;
                    pos[addr + 2] += offset.z;
                } else {
                    // Set the root body's position directly...
                    let root = this.model.body_rootid[b];
                    let addr = this.model.jnt_qposadr[this.model.body_jntadr[root]];
                    let pos = this.data.qpos;
                    pos[addr + 0] += offset.x;
                    pos[addr + 1] += offset.y;
                    pos[addr + 2] += offset.z;
                }
            }

            mujoco.mj_forward(this.model, this.data);
        }

        // Update body transforms.
        for (let b = 0; b < this.model.nbody; b++) {
            if (this.bodies[b]) {
                getPosition(this.data.xpos, b, this.bodies[b].position);
                getQuaternion(this.data.xquat, b, this.bodies[b].quaternion);
                this.bodies[b].updateWorldMatrix();
            }
        }

        // Update light transforms.
        for (let l = 0; l < this.model.nlight; l++) {
            if (this.lights[l]) {
                getPosition(this.data.light_xpos, l, this.lights[l].position);
                getPosition(this.data.light_xdir, l, this.tmpVec);
                this.lights[l].lookAt(this.tmpVec.add(this.lights[l].position));
            }
        }

        // --- MQTT Publish State ---
        if (this.mqttClient && this.mqttClient.connected) {
            const now = performance.now();
            if (!this._lastMqttPub) this._lastMqttPub = 0;
            if (now - this._lastMqttPub > 33) { // ~30Hz
                this._lastMqttPub = now;
                const state = {
                    time: this.data.time,
                    qpos: Array.from(this.data.qpos)
                };
                const topic = `reachy/${this.mqttParams.robotId}/state`;
                this.mqttClient.publish(topic, JSON.stringify(state));
            }
        }

        // Draw Tendons and Flex verts
        drawTendonsAndFlex(this.mujocoRoot, this.model, this.data);

        // Render!
        this.renderer.render(this.scene, this.camera);
    }
}

async function downloadReachyAssets(mujoco) {
    try {
        const response = await fetch("./assets/reachy_mini/config.json");
        const config = await response.json();
        const allFiles = config.assets;

        let requests = allFiles.map((url) => fetch("./assets/" + url));
        let responses = await Promise.all(requests);

        for (let i = 0; i < responses.length; i++) {
            if (!responses[i].ok) {
                console.warn("Failed to load asset: " + allFiles[i]);
                continue;
            }

            let split = allFiles[i].split("/");
            let working = '/working/';
            for (let f = 0; f < split.length - 1; f++) {
                working += split[f];
                if (!mujoco.FS.analyzePath(working).exists) { mujoco.FS.mkdir(working); }
                working += "/";
            }

            let isBinary = allFiles[i].endsWith(".stl") || allFiles[i].endsWith(".png") || allFiles[i].endsWith(".part");
            if (isBinary) {
                mujoco.FS.writeFile("/working/" + allFiles[i], new Uint8Array(await responses[i].arrayBuffer()));
            } else {
                mujoco.FS.writeFile("/working/" + allFiles[i], await responses[i].text());
            }
        }
    } catch (e) {
        console.error("Critical error loading Reachy assets:", e);
    }
}

let demo = new MuJoCoDemo();
await demo.init();
