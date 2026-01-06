import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { localPost, peerPost } from "../services/api";

export default function UploadFile() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [encryptedFile, setEncryptedFile] = useState(null);
  const [encryptedFileName, setEncryptedFileName] = useState(null);
  const [encryptedFilePath, setEncryptedFilePath] = useState(null);
  const [aesKey, setAesKey] = useState(null);
  const [encryptedAesKey, setEncryptedAesKey] = useState(null);
  const [hash, setHash] = useState(null);
  const [signature, setSignature] = useState(null);
  const [receiverPublicKey, setReceiverPublicKey] = useState(null);
  const [senderPrivateKey, setSenderPrivateKey] = useState(null);
  
  const [encrypting, setEncrypting] = useState(false);
  const [sending, setSending] = useState(false);
  const [animationStep, setAnimationStep] = useState(0);
  const [error, setError] = useState(null);
  
  const navigate = useNavigate();

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    
    if (file) {
      if (file.type !== "application/pdf") {
        setError("Please select a PDF file");
        return;
      }
      
      if (file.size > 100 * 1024 * 1024) {
        setError("File size must be less than 100MB");
        return;
      }

      setEncrypting(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append("file", file);
        
        const result = await localPost("/encrypt", formData,true);

        setSelectedFile(file);
        setEncryptedFile(result.encrypted_file);
        setEncryptedFileName(result.encrypted_file_name);
        setEncryptedFilePath(result.encrypted_path);
        setAesKey(result.aes_key);
        setEncryptedAesKey(result.encrypted_aes_key);
        setHash(result.file_hash);
        setSignature(result.signature);
        setReceiverPublicKey(result.receiver_public_key);
        setSenderPrivateKey(result.signature_private_key);
        
      } catch (err) {
        console.error("Encryption failed:", err);
        setError("Encryption failed. Please try again.");
        setSelectedFile(null);
      } finally {
        setEncrypting(false);
      }
    }
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    
    if (file) {
      if (file.type !== "application/pdf") {
        setError("Please select a PDF file");
        return;
      }
      
      if (file.size > 100 * 1024 * 1024) {
        setError("File size must be less than 100MB");
        return;
      }

      setEncrypting(true);
      setError(null);

      try {
        const formData = new FormData();
        formData.append("file", file);
        
        const result = await localPost("/encrypt", formData, true);
        
        setSelectedFile(file);
        setEncryptedFile(result.encrypted_file);
        setEncryptedFileName(result.encrypted_file_name);
        setEncryptedFilePath(result.encrypted_file_path);
        setAesKey(result.aes_key);
        setEncryptedAesKey(result.encrypted_aes_key);
        setHash(result.file_hash);
        setSignature(result.signature);
        setReceiverPublicKey(result.receiver_public_key);
        setSenderPrivateKey(result.sender_private_key);
        
      } catch (err) {
        console.error("Encryption failed:", err);
        setError("Encryption failed. Please try again.");
        setSelectedFile(null);
      } finally {
        setEncrypting(false);
      }
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const sendFile = async () => {
    setSending(true);
    setError(null);
    setAnimationStep(0);

    // Step 1: Show AES encryption
    setTimeout(() => setAnimationStep(1), 500);
    
    // Step 2: Show RSA encapsulation of AES key
    setTimeout(() => setAnimationStep(2), 2500);
    
    // Step 3: Show hashing
    setTimeout(() => setAnimationStep(3), 4500);
    
    // Step 4: Show digital signature
    setTimeout(() => setAnimationStep(4), 6500);
    
    // Step 5: Show sending rocket
    setTimeout(async () => {
      setAnimationStep(5);
      
      try {
        const formData = new FormData();
        
        // Create a file object from encrypted file path (you'll need to handle this)
        formData.append("encrypted_file", encryptedFile);
        formData.append("encrypted_aes_key", encryptedAesKey);
        formData.append("signature", signature);
        formData.append("original_filename", selectedFile.name);
        
        const result = await peerPost("/decrypt", formData, true);
        
        console.log("File sent successfully:", result);
        
        // Navigate to success page
        setTimeout(() => {
          navigate("/filesent");
        }, 2000);
        
      } catch (err) {
        console.error("Send failed:", err);
        setError("Failed to send file. Please try again.");
        setSending(false);
        setAnimationStep(0);
      }
    }, 8500);
  };

  const removeFile = () => {
    setSelectedFile(null);
    setEncryptedFileName(null);
    setEncryptedFilePath(null);
    setAesKey(null);
    setEncryptedAesKey(null);
    setHash(null);
    setSignature(null);
    setReceiverPublicKey(null);
    setSenderPrivateKey(null);
    setError(null);
    setAnimationStep(0);
  };

  const goBack = () => {
    navigate("/sender");
  };

  const truncate = (str, len = 20) => {
    if (!str) return "";
    return str.length > len ? str.substring(0, len) + "..." : str;
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-6">
      <div className="w-full max-w-4xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <button
            onClick={goBack}
            className="mb-4 text-slate-400 hover:text-white transition flex items-center gap-2 mx-auto"
          >
            <span>←</span> Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold mb-2">Send PDF Document</h1>
          <p className="text-slate-400">Secure end-to-end encrypted file transfer</p>
        </div>

        {/* Upload Area */}
        <div className="bg-slate-800 rounded-xl p-8 shadow-xl">
          {!selectedFile ? (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="border-2 border-dashed border-slate-600 rounded-lg p-12 text-center hover:border-indigo-500 transition cursor-pointer"
              onClick={() => document.getElementById("fileInput").click()}
            >
              {encrypting ? (
                <div className="space-y-4">
                  <div className="text-6xl animate-pulse">🔐</div>
                  <h3 className="text-xl font-semibold">Encrypting file...</h3>
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              ) : (
                <>
                  <div className="mb-4">
                    <span className="text-6xl">📄</span>
                  </div>
                  <h3 className="text-xl font-semibold mb-2">Drop your PDF here</h3>
                  <p className="text-slate-400 mb-4">or click to browse</p>
                  <p className="text-sm text-slate-500">Maximum file size: 100MB</p>
                  <p className="text-xs text-slate-600 mt-2">
                    🔒 Files are automatically encrypted using AES-256
                  </p>
                </>
              )}
              
              <input
                id="fileInput"
                type="file"
                accept="application/pdf"
                onChange={handleFileSelect}
                className="hidden"
                disabled={encrypting}
              />
            </div>
          ) : (
            <div className="space-y-6">
              {/* File Info */}
              <div className="bg-slate-700 rounded-lg p-6 flex items-center gap-4">
                <div className="w-16 h-16 bg-red-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-3xl">📕</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold truncate">{selectedFile.name}</h4>
                  <p className="text-sm text-slate-400">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="text-xs text-emerald-400 mt-1">✓ Encrypted & Ready</p>
                </div>
                {!sending && (
                  <button
                    onClick={removeFile}
                    className="text-red-400 hover:text-red-300 transition"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Animation Steps */}
              {sending && (
                <div className="bg-slate-700 rounded-lg p-6 space-y-6">
                  {/* Step 1: AES Encryption */}
                  <div className={`transition-all duration-500 ${animationStep >= 1 ? 'opacity-100' : 'opacity-30'}`}>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="w-10 h-10 rounded-full bg-indigo-500 flex items-center justify-center flex-shrink-0">
                        {animationStep > 1 ? '✓' : '1'}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold">AES-256 Encryption</h4>
                        <p className="text-sm text-slate-400">File encrypted with symmetric key</p>
                      </div>
                    </div>
                    {animationStep === 1 && (
                      <div className="ml-14 bg-slate-800 p-4 rounded animate-fade-in">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-2xl animate-pulse">🔑</span>
                          <span className="text-xs text-slate-400">AES Key:</span>
                        </div>
                        <code className="text-xs text-indigo-300 break-all block">
                          {truncate(aesKey, 60)}
                        </code>
                      </div>
                    )}
                  </div>

                  {/* Step 2: RSA Encapsulation */}
                  <div className={`transition-all duration-500 ${animationStep >= 2 ? 'opacity-100' : 'opacity-30'}`}>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="w-10 h-10 rounded-full bg-purple-500 flex items-center justify-center flex-shrink-0">
                        {animationStep > 2 ? '✓' : '2'}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold">RSA Key Encapsulation</h4>
                        <p className="text-sm text-slate-400">AES key encrypted with receiver's public key</p>
                      </div>
                    </div>
                    {animationStep === 2 && (
                      <div className="ml-14 bg-slate-800 p-4 rounded animate-fade-in space-y-3">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl animate-bounce">🔐</span>
                          <span className="text-xs text-slate-400">Receiver's Public Key:</span>
                        </div>
                        <code className="text-xs text-purple-300 break-all block">
                          {truncate(receiverPublicKey, 60)}
                        </code>
                        <div className="text-center text-2xl animate-pulse">⬇</div>
                        <code className="text-xs text-emerald-300 break-all block">
                          {truncate(encryptedAesKey, 60)}
                        </code>
                      </div>
                    )}
                  </div>

                  {/* Step 3: Hashing */}
                  <div className={`transition-all duration-500 ${animationStep >= 3 ? 'opacity-100' : 'opacity-30'}`}>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="w-10 h-10 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0">
                        {animationStep > 3 ? '✓' : '3'}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold">SHA-256 Hashing</h4>
                        <p className="text-sm text-slate-400">Generating file integrity hash</p>
                      </div>
                    </div>
                    {animationStep === 3 && (
                      <div className="ml-14 bg-slate-800 p-4 rounded animate-fade-in">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-2xl animate-spin-slow">#️⃣</span>
                          <span className="text-xs text-slate-400">File Hash:</span>
                        </div>
                        <code className="text-xs text-blue-300 break-all block">
                          {truncate(hash, 64)}
                        </code>
                      </div>
                    )}
                  </div>

                  {/* Step 4: Digital Signature */}
                  <div className={`transition-all duration-500 ${animationStep >= 4 ? 'opacity-100' : 'opacity-30'}`}>
                    <div className="flex items-center gap-4 mb-3">
                      <div className="w-10 h-10 rounded-full bg-orange-500 flex items-center justify-center flex-shrink-0">
                        {animationStep > 4 ? '✓' : '4'}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold">Digital Signature</h4>
                        <p className="text-sm text-slate-400">Signed with sender's private key</p>
                      </div>
                    </div>
                    {animationStep === 4 && (
                      <div className="ml-14 bg-slate-800 p-4 rounded animate-fade-in space-y-3">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl animate-pulse">✍️</span>
                          <span className="text-xs text-slate-400">Sender's Private Key:</span>
                        </div>
                        <code className="text-xs text-orange-300 break-all block">
                          {truncate(senderPrivateKey, 60)}
                        </code>
                        <div className="text-center text-2xl animate-pulse">⬇</div>
                        <code className="text-xs text-emerald-300 break-all block">
                          {truncate(signature, 60)}
                        </code>
                      </div>
                    )}
                  </div>

                  {/* Step 5: Sending */}
                  {animationStep === 5 && (
                    <div className="text-center py-8 animate-fade-in">
                      <div className="text-8xl mb-4 animate-rocket">🚀</div>
                      <h3 className="text-2xl font-bold text-emerald-400 mb-2">Sending File...</h3>
                      <p className="text-slate-400">Transmitting encrypted data to receiver</p>
                      <div className="mt-4 flex items-center justify-center gap-2">
                        <div className="w-3 h-3 bg-emerald-500 rounded-full animate-ping"></div>
                        <div className="w-3 h-3 bg-emerald-500 rounded-full animate-ping" style={{ animationDelay: '0.2s' }}></div>
                        <div className="w-3 h-3 bg-emerald-500 rounded-full animate-ping" style={{ animationDelay: '0.4s' }}></div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error Message */}
              {error && (
                <div className="bg-red-500/20 border border-red-500 rounded-lg p-4 flex items-center gap-3">
                  <span className="text-2xl">⚠</span>
                  <span className="text-red-400">{error}</span>
                </div>
              )}

              {/* Send Button */}
              {!sending && (
                <button
                  onClick={sendFile}
                  className="w-full py-4 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 font-semibold transition flex items-center justify-center gap-2 shadow-lg hover:shadow-xl"
                >
                  <span>🚀</span>
                  Send Encrypted File
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}