import { useState } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";

import RoleSelector from "./components/RoleSelector";
import ProtectedRoute from "./components/ProtectedRoute";

import SenderDashboard from "./pages/SenderDashboard";
import ReceiverDashboard from "./pages/ReceiverDashboard";

import UploadFile from "./pages/UploadFile";
import DownloadFile from "./pages/DownloadFile";

export default function App() {
  const [role, setRole] = useState(null);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public route */}
        <Route
          path="/"
          element={<RoleSelector onRoleSelected={setRole} />}
        />

        {/* Sender-only */}
        <Route
          path="/sender"
          element={
            <ProtectedRoute role={role} allowed={["SENDER"]}>
              <SenderDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/upload-file"
          element={
            <ProtectedRoute role={role} allowed={["SENDER"]}>
              <UploadFile />
            </ProtectedRoute>
          }
        />

        {/* Receiver-only */}
        <Route
          path="/receiver"
          element={
            <ProtectedRoute role={role} allowed={["RECEIVER"]}>
              <ReceiverDashboard />
            </ProtectedRoute>
          }
        />

         <Route
          path="/download-file"
          element={
            <ProtectedRoute role={role} allowed={["RECEIVER"]}>
              <DownloadFile />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
