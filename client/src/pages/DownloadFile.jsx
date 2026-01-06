import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { localGet } from "../services/api";

export default function DownloadFile() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const pollIntervalRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Start polling for files
    pollForFiles();
    
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const pollForFiles = () => {
    pollIntervalRef.current = setInterval(async () => {
      try {
        const response = await fetch("http://localhost:5000/next-file");
        
        if (response.status === 200) {
          const result = await response.json();
          
          // Add new file to list
          setFiles(prevFiles => [...prevFiles, {
            id: result.id,
            filename: result.filename,
            fileData: result.file_data,
            fileSize: result.file_size
          }]);
          
          setLoading(false);
        } else if (response.status === 204) {
          // No files available yet, keep polling
          setLoading(true);
        }
      } catch (err) {
        console.error("Polling error:", err);
        setError("Connection error");
      }
    }, 2000); // Poll every 2 seconds
  };

  const downloadFile = (file) => {
    try {
      // Decode base64 to binary
      const binaryString = atob(file.fileData);
      const bytes = new Uint8Array(binaryString.length);
      
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      
      // Create blob and download
      const blob = new Blob([bytes], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.filename;
      document.body.appendChild(a);
      a.click();
      
      // Cleanup
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      // Remove from UI after download
      setFiles(prevFiles => prevFiles.filter(f => f.id !== file.id));
    } catch (err) {
      console.error("Download failed:", err);
      setError("Failed to download file");
    }
  };

  const goBack = () => {
    navigate("/receiver");
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <button
            onClick={goBack}
            className="mb-4 text-slate-400 hover:text-white transition flex items-center gap-2 mx-auto"
          >
            <span>←</span> Back to Dashboard
          </button>
          <h1 className="text-3xl font-bold mb-2">Receive PDF Documents</h1>
          <p className="text-slate-400">Waiting for incoming files...</p>
        </div>

        {/* Waiting State */}
        {loading && files.length === 0 && (
          <div className="bg-slate-800 rounded-xl p-12 shadow-xl text-center">
            <div className="mb-6">
              <span className="text-6xl animate-pulse">📥</span>
            </div>
            <h3 className="text-xl font-semibold mb-2">Ready to Receive</h3>
            <p className="text-slate-400">
              Files sent from the sender will appear here
            </p>
            <div className="mt-6 flex items-center justify-center gap-2 text-indigo-400">
              <span className="animate-ping inline-block w-2 h-2 bg-indigo-400 rounded-full"></span>
              <span>Listening...</span>
            </div>
          </div>
        )}

        {/* Files List */}
        {files.length > 0 && (
          <div className="bg-slate-800 rounded-xl p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-semibold mb-4">Received Files</h3>
            
            {files.map((file) => (
              <div
                key={file.id}
                className="bg-slate-700 rounded-lg p-6 flex items-center gap-4 hover:bg-slate-650 transition animate-fade-in"
              >
                <div className="w-16 h-16 bg-red-500 rounded-lg flex items-center justify-center flex-shrink-0">
                  <span className="text-3xl">📕</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold truncate">{file.filename}</h4>
                  <p className="text-sm text-slate-400">
                    {(file.fileSize / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <p className="text-xs text-emerald-400 mt-1">✓ Decrypted & Ready</p>
                </div>
                <button
                  onClick={() => downloadFile(file)}
                  className="px-6 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold transition flex items-center gap-2"
                >
                  <span>⬇</span>
                  Download
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mt-4 bg-red-500/20 border border-red-500 rounded-lg p-4 flex items-center gap-3">
            <span className="text-2xl">⚠</span>
            <span className="text-red-400">{error}</span>
          </div>
        )}

        {/* Continue Listening Message */}
        {files.length > 0 && (
          <div className="mt-4 text-center">
            <p className="text-sm text-slate-500 flex items-center justify-center gap-2">
              <span className="animate-ping inline-block w-2 h-2 bg-indigo-400 rounded-full"></span>
              Still listening for more files...
            </p>
          </div>
        )}
      </div>
    </div>
  );
}