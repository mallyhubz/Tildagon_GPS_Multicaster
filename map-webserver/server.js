import WebSocket, { WebSocketServer } from "ws";
import http from "http";
import fs from "fs";
import dgram from "node:dgram";
import os from "os";

// ------------------------------
// HTTP server (serves index.html)
// ------------------------------
const server = http.createServer((req, res) => {
    if (req.url === "/") {
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(fs.readFileSync("index.html"));
    }
	if (req.url === "/emfmap.html") {
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end(fs.readFileSync("emfmap.html"));
    }
});

// ------------------------------
// WebSocket server
// ------------------------------
const wss = new WebSocketServer({ server });

function broadcast(obj) {
    const msg = JSON.stringify(obj);
    for (const client of wss.clients) {
        if (client.readyState === WebSocket.OPEN) {
            client.send(msg);
        }
    }
}

// ------------------------------
// UDP multicast listener
// ------------------------------
const MCAST_ADDR = "239.71.80.83";
const UDP_PORT = 6969;

// Pick the correct NIC automatically
const ifaces = os.networkInterfaces();
let ifaceIP = null;

for (const name of Object.keys(ifaces)) {
    for (const iface of ifaces[name]) {
        if (iface.family === "IPv4" && !iface.internal) {
            ifaceIP = iface.address;
        }
    }
}

console.log("Using interface:", ifaceIP);

const udp = dgram.createSocket({ type: "udp4", reuseAddr: true });

udp.on("error", (err) => {
    console.error("UDP ERROR:", err);
});

udp.on("listening", () => {
    console.log("UDP listening on", UDP_PORT);

    udp.setMulticastLoopback(true);
    udp.setMulticastTTL(1);

    try {
        udp.addMembership(MCAST_ADDR, ifaceIP);
        console.log("Joined multicast group", MCAST_ADDR, "on", ifaceIP);
    } catch (e) {
        console.error("addMembership failed:", e);
    }
});

udp.on("message", (msg, rinfo) => {
    console.log("UDP:", msg.toString(), rinfo);

    const text = msg.toString().trim();
    const parts = text.split(",");
    if (parts.length !== 3) return;

    const [label, latStr, lonStr] = parts;
    const lat = parseFloat(latStr);
    const lon = parseFloat(lonStr);

    if (!isFinite(lat) || !isFinite(lon)) return;

    broadcast({ label, lat, lon });
});

udp.bind(UDP_PORT, "0.0.0.0");

// ------------------------------
// Start HTTP + WS server
// ------------------------------
server.listen(8080, () => {
    console.log("Web server + WS on http://localhost:8080");
});
