import { useState, useEffect } from "react"
import "./App.css"

function App() {
  const [msg, setMsg] = useState("")
  const [consentId, setConsentId] = useState("")
  const [status, setStatus] = useState("")

  // Flask API base URL
  const API_BASE = "https://740a29f7-090b-424b-aa48-0bd1e64a213d-00-131hf83hco1da.spock.replit.dev:8080"

  const startConsent = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/initiate-consent`, { method: "POST" })
      const data = await res.json()
      console.log("Consent response:", data)
      if (data.id) {
        setConsentId(data.id)
        setMsg("Consent initiated! Please approve it.")
      }
      if (data.url) {
        window.open(data.url, "_blank")
      }
    } catch (err) {
      console.error("Error starting consent:", err)
      setMsg("Error initiating consent")
    }
  }

  const checkStatus = async () => {
    if (!consentId) {
      setMsg("No consent started yet")
      return
    }
    try {
      const res = await fetch(`${API_BASE}/api/consent-status/${consentId}`)
      const data = await res.json()
      console.log("Consent status:", data)
      if (data.status) {
        setStatus(data.status)
        setMsg(`Consent status: ${data.status}`)
      } else {
        setMsg("Unable to fetch status")
      }
    } catch (err) {
      console.error("Error checking consent status:", err)
      setMsg("Error checking consent status")
    }
  }

  useEffect(() => {
    fetch(`${API_BASE}/api/hello`)
      .then(res => res.json())
      .then(data => setMsg(data.message))
      .catch(err => console.error("Error fetching message:", err))
  }, [])

  return (
    <div>
      <h1>{msg}</h1>
      <button onClick={startConsent}>Start Consent Flow</button>
      {consentId && (
        <div>
          <p>Consent ID: {consentId}</p>
          <button onClick={checkStatus}>Check Consent Status</button>
          {status && <p>Status: {status}</p>}
        </div>
      )}
    </div>
  )
}

export default App
