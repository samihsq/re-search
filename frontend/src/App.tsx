import React from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Box } from "@mui/material";

// Import components
import LandingPage from "./components/LandingPage";
import SimpleResearchOpportunities from "./components/SimpleResearchOpportunities";
import EnhancedResearchOpportunities from "./components/EnhancedResearchOpportunities";
import Header from "./components/Header";

function App() {
  const location = useLocation();
  const showHeader = location.pathname !== "/";

  return (
    <Box className="App">
      {showHeader && <Header />}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/home" element={<SimpleResearchOpportunities />} />
        <Route path="/enhanced" element={<EnhancedResearchOpportunities />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Box>
  );
}

export default App;
