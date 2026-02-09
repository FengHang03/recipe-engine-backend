import { useEffect, useState } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
} from "firebase/auth";
import {apiFetch} from "../lib/api"
import type { User } from "firebase/auth";
import { auth } from "../lib/firebase";

export default function AuthTest() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string>("");

  // 等价于 Firebase demo 里的 onAuthStateChanged
  useEffect(() => {
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
    });
    return () => unsub();
  }, []);

  async function handleSignIn() {
    setError("");
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleSignUp() {
    setError("");
    try {
      const cred = await createUserWithEmailAndPassword(auth, email, password);
      await sendEmailVerification(cred.user);
      alert("Verification email sent");
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function handleResetPassword() {
    setError("");
    try {
      await sendPasswordResetEmail(auth, email);
      alert("Password reset email sent");
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 420 }}>
      <h2>Firebase Email / Password Auth Test</h2>

      <input
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <br />
      <input
        placeholder="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <div style={{ marginTop: 12 }}>
        {!user ? (
          <>
          <button onClick={handleSignIn}>Sign In</button>
          <button onClick={handleSignUp} style={{ marginLeft: 8 }}>
            Sign Up
          </button>
          <button onClick={handleResetPassword} style={{ marginLeft: 8 }}>
            Reset Password
          </button>
          </>
        ) : (
          <>
            <button
              onClick={async () => {
                const token = await auth.currentUser?.getIdToken();
                console.log("idToken length", token?.length);
                const data = await apiFetch<{ uid: string; email?: string }>("/me");
                console.log("me:", data);
                alert(JSON.stringify(data, null, 2));
              }} style={{ marginLeft: 8 }}
            >
              Call /me
            </button>

            <button onClick={async () => {
              try {
                const res = await apiFetch<{ ok: boolean }>("/ping");
                alert('ping result: ${res.ok}');
              } catch (e: any) {
                alert('ping failed: ${e.message}');
              }
            }} style={{ marginLeft: 8 }}
            >
              Ping 
            </button>
          </>
        )}
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <hr />

      <h4>Auth State</h4>
      {user ? (
        <pre>{JSON.stringify({ uid: user.uid, email: user.email }, null, 2)}</pre>
      ) : (
        <p>Not signed in</p>
      )}
    </div>
  );
}
