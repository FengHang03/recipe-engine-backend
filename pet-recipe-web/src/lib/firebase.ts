// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getAnalytics } from "firebase/analytics";
import { getFirestore, collection, getDocs } from 'firebase/firestore'
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBJtF42aI-9kGOse_Jo9uGGnroj4Wn-6sg",
  authDomain: "project-36d4843f-b026-466b-bd4.firebaseapp.com",
  projectId: "project-36d4843f-b026-466b-bd4",
  storageBucket: "project-36d4843f-b026-466b-bd4.firebasestorage.app",
  messagingSenderId: "566938495998",
  appId: "1:566938495998:web:4625917dd94cd40364eeaf",
  measurementId: "G-JJK22NX82C"
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const analytics = getAnalytics(app);
export const db = getFirestore(app);

export default app;