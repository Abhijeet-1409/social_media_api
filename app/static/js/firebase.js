
// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.1.0/firebase-app.js";
import { getMessaging, getToken, onMessage, deleteToken } from "https://www.gstatic.com/firebasejs/11.1.0/firebase-messaging.js";

let app, messaging, vapidKey, firebaseConfig;


const initializeFirebase = async () => {
    try {
        const response = await fetch('http://localhost:8000/firebaseConfig-and-vapidKey', { method: "GET" });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(`HTTP error while fetching firebaseConfig with status ${response.status}: ${data}`);
        }
        firebaseConfig = data.firebaseConfig;
        vapidKey = data.vapidKey;
        app = initializeApp(firebaseConfig);
        messaging = getMessaging(app);
        return messaging;
    } catch (error) {
        console.error(error);
        throw error;
    }
};


const messagingReady = initializeFirebase();

export { app, messaging, vapidKey, getToken, onMessage, messagingReady, deleteToken, firebaseConfig };

