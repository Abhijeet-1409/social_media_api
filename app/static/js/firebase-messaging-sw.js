importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');



const firebaseConfig = {
    apiKey: "AIzaSyC-TiVXQumh_gc2xTft9ADR5MJtRPHtma0",
    authDomain: "push-notification-5932c.firebaseapp.com",
    projectId: "push-notification-5932c",
    storageBucket: "push-notification-5932c.firebasestorage.app",
    messagingSenderId: "251116402389",
    appId: "1:251116402389:web:65aa2fda2da2beb176145c",
    measurementId: "G-MSCBZMLTXE"
};

firebase.initializeApp(firebaseConfig);


const messaging = firebase.messaging();

messaging.onMessage((payload) => {
    const notificationTitle = payload?.notification?.title | 'Background Message Title';
    const notificationOptions = {
        body: payload?.notification?.body | 'Background Message body.',
    };
    self.registration.showNotification(notificationTitle, notificationOptions);
});



self.addEventListener('push', function (event) {
    console.log("Receive a push event from firebase cloud messaging");
    const payload = event.data.json();
    const clientId = payload.data.clientId;
    const message = payload.notification.body;
    const notificationTitle = payload.notification.title;
    event.waitUntil(
        self.clients.matchAll({ includeUncontrolled: true, type: 'window' }).then(clients => {
            clients.forEach(client => {
                if (client.id === clientId && client.visibilityState === 'hidden') {
                    client.postMessage({
                        type: "PUSH_NOTIFICATION",
                        text: message
                    })
                }

            });
        })
    );
});



self.addEventListener("message", (event) => {
    const type = event.data.type;
    console.log("Message type recieved from main thread : ", type);
    if (type === "REQUEST_CLIENT_ID") {
        const clientId = event.source.id;
        event.source.postMessage({ type: "CLIENT_ID", clientId: clientId });
    }


    if (type === "SET_TIMEOUT") {
        const timestr = event.data.time;
        const clientId = event.source.id;
        const expireTime = new Date(timestr);
        const timeDiff = expireTime - Date.now();
        if (timeDiff > 0) {
            const timer = setTimeout(() => {
                self.clients.matchAll().then((clients) => {
                    let clientFound = false;
                    clients.forEach(client => {
                        if (client.id === clientId) {
                            client.postMessage({
                                type: "TOKEN_EXPIRE",
                            })
                        }
                    });

                    if (!clientFound) {
                        console.warn(`Client with id ${clientId} not found.`);
                    }

                }).catch(error => {
                    console.error("Error while matching clients:", error);
                });

            }, timeDiff);

            event.source.postMessage({
                type: "TIMER_SETUP_SUCCESSFULLY",
            })
        }
        else {
            event.source.postMessage({
                type: "TIMER_SETUP_FAILED",
            })
        }
    }
})

