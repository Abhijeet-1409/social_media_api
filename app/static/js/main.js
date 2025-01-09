import { messaging, vapidKey, getToken, onMessage, deleteToken, messagingReady, firebaseConfig } from "./firebase.js";


(async () => {
    try {
        const messaging = await messagingReady;

        // Setup onMessage listener
        onMessage(messaging, (payload) => {
            console.log("Message received from Firebase Cloud Messaging HTTP v1");
            const message = payload.notification.body;
            addNotification(message);
        });
    } catch (error) {
        console.error("Failed to initialize messaging:", error);
    }
})();



async function clearServiceWorkers() {
    console.log("Clear old service-worker");
    if ('serviceWorker' in navigator) {
        try {
            // Get all service worker registrations
            const registrations = await navigator.serviceWorker.getRegistrations();

            // Loop through each registration and unregister it
            for (const registration of registrations) {
                await registration.unregister();
                console.log(`Service Worker unregistered: ${registration.scope}`);
            }

            console.log("All existing service workers have been removed.");
        } catch (error) {
            console.error("Error removing service workers:", error);
        }
    } else {
        console.warn("Service Workers are not supported in this browser.");
    }
}



async function registerServiceWorker() {

    await clearServiceWorkers();
    let jwtExpireTime = localStorage.getItem('jwtExpireTime');
    console.log("Register service-worker");
    if ('serviceWorker' in navigator) {
        try {
            const firebaseRegistration = await navigator.serviceWorker.register("/firebase-messaging-sw.js");
            firebaseRegistration.update();
            console.log('firebase Service Worker registered with scope:', firebaseRegistration.scope);
            const firebaseReadyRegistration = await navigator.serviceWorker.ready;
            if (firebaseReadyRegistration.active) {
                firebaseReadyRegistration.active.postMessage({ type: "REQUEST_CLIENT_ID" });
                firebaseReadyRegistration.active.postMessage({ type: "SET_TIMEOUT", time: jwtExpireTime });
            }
            else {
                console.warn('No active service worker found.');
            }
        } catch (err) {
            console.error('Error occured ', err);
        }

    } else {
        console.warn('Service Workers are not supported in this browser.');
    }
}

function grantPermission() {
    console.log("Access notification permission status")
    Notification.requestPermission()
        .then((permission) => {
            if (permission === "granted") {
                console.log("permission is granted");
                return registerServiceWorker();
            }
            else {
                throw "Denied permission";
            }
        })
        .catch((err) => {
            console.error('Error occured ', err)
            alert("Please grant permission for notification");
        });

}

class HttpException extends Error {
    constructor(message, status) {
        super(message);
        this.statusCode = status;
    }
}

async function getFcmToken() {
    console.log("Fetch fcm token");
    try {
        let fcmToken = localStorage.getItem("fcmToken");
        let currentToken = fcmToken ? fcmToken : await getToken(messaging, { vapidKey });
        if (currentToken) {
            if (fcmToken !== currentToken) {
                localStorage.setItem("fcmToken", currentToken);
            }
        } else {
            console.log('No registration token available. Request permission to generate one.');
        }
    } catch (err) {
        console.error('An error occurred while retrieving token. ', err);
    }


}

async function deleteFcmToken() {
    console.log("Delete fcm token");
    try {
        await deleteToken(messaging);
    } catch (err) {
        console.error('An error occurred while retrieving token. ', err);
    }
}


async function registerFcmTOken() {

    try {
        await getFcmToken();
        console.log("Register fcm token on server");
        let clientId = localStorage.getItem("clientId");
        let fcmToken = localStorage.getItem("fcmToken");
        let jwtToken = localStorage.getItem('jwtToken');
        let jwtTokenType = localStorage.getItem('jwtTokenType');
        if (!fcmToken) {
            return;
        }
        let url = "http://localhost:8000/users/notifications/register";
        let response = await fetch(url, {
            method: "POST",
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `${jwtTokenType} ${jwtToken}`,
            },
            body: JSON.stringify({ // Convert object to JSON string
                "fcm_token": fcmToken,
                "client_id": clientId,
            })
        });
        let data = await response.json();
        if (!response.ok) {
            // console.log(data);
            // console.log(response);
            let message;
            switch (response.status) {
                case 401:
                    message = "Not authorize for this request";
                    break;
                case 422:
                    message = "Validation error for fcm token";
                    break;
                default:
                    message = "Internal server error";
                    break;
            }
            throw new HttpException(message, response.status);
        }

    } catch (err) {
        if (err instanceof HttpException) {
            console.error(`${err.name} - ${err.message}: ${err.statusCode}`);
        } else {
            // Catch all other types of errors
            console.error("An unexpected error occurred:", err);
        }
    }
}


async function deRegisterFcmToken(params) {
    console.log("Deregister fcm token from server");
    try {
        let url = "http://localhost:8000/users/notification/deregister";
        let clientId = localStorage.getItem("clientId");
        let fcmToken = localStorage.getItem("fcmToken");
        let jwtToken = localStorage.getItem('jwtToken');
        let jwtTokenType = localStorage.getItem('jwtTokenType');
        let response = await fetch(url, {
            method: "PUT",
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `${jwtTokenType} ${jwtToken}`,
            },
            body: JSON.stringify({ // Convert object to JSON string
                "fcm_token": fcmToken,
                "client_id": clientId,
            })
        });
        let data = await response.json();
        if (!response.ok) {
            let message;
            // console.log(data);
            // console.log(response);
            switch (response.status) {
                case 401:
                    message = "Not authorize for this request";
                    break;
                case 404:
                    message = "Active user not found";
                    break;
                case 422:
                    message = "Validation error for fcm token";
                    break;
                default:
                    message = "Internal server error";
                    break;
            }
            throw new HttpException(message, response.status);
        }

    } catch (err) {
        if (err instanceof HttpException) {
            console.error(`${err.name} - ${err.message}: ${err.statusCode}`);
        } else {
            // Catch all other types of errors
            console.error("An unexpected error occurred:", err);
        }
    }
}


async function authentication(username, password) {
    console.log("Authenticate user");
    try {
        let url = "http://localhost:8000/login";
        let response = await fetch(url, {
            method: "POST",
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                "username": username,
                "password": password
            })
        });

        if (!response.ok) {
            let message;
            switch (response.status) {
                case 401:
                    message = "Not authorize for this request";
                    break;
                case 404:
                    message = "User not found";
                    break;
                case 422:
                    message = "Not a valid username or password"
                    break;
                default:
                    message = "Internal server error";
                    break;
            }
            throw new HttpException(message, response.status);
        }

        let data = await response.json();
        let jwtToken = data.access_token;
        let jwtTokenType = data.token_type;
        let jwtExpireTime = data.expire_time;
        localStorage.setItem("username", username);
        localStorage.setItem("jwtToken", jwtToken);
        localStorage.setItem("jwtTokenType", jwtTokenType);
        localStorage.setItem("jwtExpireTime", jwtExpireTime);

    } catch (err) {
        if (err instanceof HttpException) {
            console.error(`${err.name} - ${err.message}: ${err.statusCode}`);
        } else {
            // Catch all other types of errors
            console.error("An unexpected error occurred:", err);
        }

    }
}



const loginDialog = document.getElementById("login-dialog");
const loginButton = document.getElementById("login-button");
const logoutDialog = document.getElementById("logout-dialog");
const logoutButton = document.getElementById("logout-button");
const notificationIconButton = document.getElementById("notificaion-icon-button");
const cancelLoginButton = document.getElementById("cancel-login-button");
const cancelLogoutButton = document.getElementById("cancel-logout-button");
const confirmLogoutButton = document.getElementById("confirm-logout");


loginButton.addEventListener("click", () => loginDialog.showModal());
cancelLoginButton.addEventListener("click", () => loginDialog.close());
logoutButton.addEventListener("click", () => logoutDialog.showModal());
cancelLogoutButton.addEventListener("click", () => logoutDialog.close());
notificationIconButton.addEventListener("click", grantPermission);


// Handle form submission
document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    if (username && password) {

        await authentication(username, password);

        loginButton.textContent = "Logged In";
        loginButton.disabled = true;
        loginButton.style.display = "none";
        logoutButton.textContent = `Logout ${username}`;
        logoutButton.style.display = "inline-block";
        notificationIconButton.style.display = "inline-block";

        alert(`Welcome, ${username}! now click on the bell icon near if you have not given permission for notification`);
        loginDialog.close();
    } else {
        alert("Both fields are required.");
    }
});



// Handle logout
async function logoutHandle() {
    await deleteFcmToken();
    await deRegisterFcmToken();
    localStorage.clear();
    loginButton.textContent = "Login";
    loginButton.disabled = false;
    loginButton.style.display = "inline-block";
    logoutButton.style.display = "none";
    notificationIconButton.style.display = "none";
    logoutDialog.close();
    alert("You have logged out.");
}

confirmLogoutButton.addEventListener("click", logoutHandle);



// Remove notification
function removeNotification(event) {
    console.log("Remove notificaiton")
    let element = event.currentTarget;
    element.classList.add('removing');
    setTimeout(() => {
        element.remove();
    }, 300);
}

// Get the template and list container
const template = document.getElementById("notification-template");
const list = document.getElementById("list");
function addNotification(message) {
    console.log("Adding notification");
    const clone = template.content.cloneNode(true);
    clone.querySelector("p").textContent = message;
    clone.querySelector('.notification').addEventListener('click', removeNotification);
    list.insertBefore(clone, list.firstChild);
}


navigator.serviceWorker.addEventListener("message", async (event) => {
    const type = event.data.type;
    console.log("Message type recieved from firebase-messaging-sw thread : ", type);
    switch (type) {
        case "CLIENT_ID": {
            localStorage.setItem("clientId", event.data.clientId);
            await registerFcmTOken();
            break;
        }
        case "PUSH_NOTIFICATION": {
            addNotification(event.data.text);
            break;
        }
        case "REQUEST_FOR_TIMER_SETUP": {
            let jwtExpireTime = localStorage.getItem("jwtExpireTime");
            navigator.serviceWorker.ready.then((registration) => {
                if (registration.active) {
                    registration.active.postMessage({
                        type: 'SET_TIMEOUT',
                        time: jwtExpireTime,
                        dest: 'timeout-sw.js',
                    });
                    console.log('Message sent to Service Worker:', 'Your message here');
                } else {
                    console.log('No active Service Worker found.');
                }
            }).catch((error) => {
                console.error('Service Worker registration failed:', error);
            })
        }
        case "TOKEN_EXPIRE": {
            alert("Your token is expired login again");
            logoutHandle();
            break;
        }
        case "TIMER_SETUP_SUCCESSFULLY": {
            console.log("Timeer setup successfully")
            break;
        }
        case "TIMER_SETUP_FAILED": {
            console.log("Timer setup failed")
            break;
        }
        default: {
            console.log("Default")
            break;
        }

    }
});

// To check animation css is working correctly
// let demoMessages = [
//     "Rahul react 😠 your post",
//     "Ramesh react 😂 your post",
//     "Shaun react 🤩 your post",
//     "Kaushal react 🤑 your post"
// ]

// demoMessages.forEach((msg, index) => {
//     let timeout = (index + 1) * 1000;
//     setTimeout(() => {
//         addNotification(msg);
//     }, timeout);
// })