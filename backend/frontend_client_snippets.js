// Example Next.js actions (place in frontend at appropriate file)
// createAccount
export async function createAccount({ fullName, email }) {
  const res = await fetch(process.env.NEXT_PUBLIC_BACKEND + '/auth/register', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ fullname: fullName, email })
  });
  return res.json();
}

// login
export async function login({ email }) {
  const res = await fetch(process.env.NEXT_PUBLIC_BACKEND + '/auth/login', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ email })
  });
  return res.json();
}

// sendEmailOTP
export async function sendEmailOTP({ email }) {
  return fetch(process.env.NEXT_PUBLIC_BACKEND + '/auth/send-otp', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ email })
  });
}

// verifyOTP
export async function verifyOTP({ accountId, passcode }) {
  const res = await fetch(process.env.NEXT_PUBLIC_BACKEND + '/auth/verify-otp', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ accountId, passcode })
  });
  return res.json();
}

// google verify (frontend should obtain id_token via Google SignIn and send)
export async function verifyGoogle(id_token) {
  const res = await fetch(process.env.NEXT_PUBLIC_BACKEND + '/auth/google/verify', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ id_token })
  });
  return res.json();
}
