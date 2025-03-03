import React, { useState, useEffect, useCallback } from "react";
import { ethers } from "ethers";
import axios from "axios";

const MetaMaskLogin = () => {
  const [account, setAccount] = useState(null);
  const [nonce, setNonce] = useState(null);
  const [authenticated, setAuthenticated] = useState(false);

  const connectWallet = async () => {
    if (!window.ethereum) {
      alert("MetaMask not detected. Please install it.");
      return;
    }

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const address = await signer.getAddress();
      setAccount(address);

      const { data } = await axios.get(`http://127.0.0.1:8000/metamask/nonce/${address}`);
      setNonce(data.nonce);
    } catch (error) {
      console.error("Error connecting wallet:", error);
    }
  };

  const signMessage = useCallback(async () => {
    if (!account || nonce === null) return;

    try {
      const provider = new ethers.BrowserProvider(window.ethereum);
      const signer = await provider.getSigner();
      const signedMessage = await signer.signMessage(`I am signing my one-time nonce: ${nonce}`);

      const { data } = await axios.post("http://127.0.0.1:8000/metamask/authenticate", {
        public_address: account,
        signature: signedMessage,
      });

      setAuthenticated(data.status === "success");
    } catch (error) {
      console.error("Error signing message:", error);
    }
  }, [account, nonce]);

  useEffect(() => {
    if (account && nonce !== null) {
      signMessage();
    }
  }, [account, nonce, signMessage]);

  return (
    <div>
      <h2>MetaMask Authentication</h2>
      {!account ? (
        <button onClick={connectWallet}>Connect MetaMask</button>
      ) : authenticated ? (
        <p style={{ color: "green" }}>✅ Authenticated!</p>
      ) : (
        <p style={{ color: "red" }}>❌ Authentication failed</p>
      )}
    </div>
  );
};

export default MetaMaskLogin;
