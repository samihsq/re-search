import React, { useState, useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { Search as SearchIcon } from "@mui/icons-material";
import { motion } from "framer-motion";

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [startFadeOut, setStartFadeOut] = useState(false);

  useEffect(() => {
    // Start fade out after 1 second
    const fadeTimer = setTimeout(() => {
      setStartFadeOut(true);
    }, 1000);

    // Navigate to home page after fade completes
    const navigationTimer = setTimeout(() => {
      navigate("/home");
    }, 2000); // 1 second display + 1 second fade

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(navigationTimer);
    };
  }, [navigate]);

  return (
    <Box
      sx={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        zIndex: 9999,
      }}
    >
      {/* Background with fade out animation */}
      <motion.div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "linear-gradient(135deg, #8C1515 0%, #651010 100%)",
          zIndex: 1,
        }}
        animate={{
          opacity: startFadeOut ? 0 : 1,
        }}
        transition={{
          duration: 1,
          ease: "easeOut",
        }}
      />

      {/* Research Logo Container */}
      <motion.div
        style={{
          position: "relative",
          zIndex: 2,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        animate={{
          opacity: startFadeOut ? 0 : 1,
        }}
        transition={{
          duration: 1,
          ease: "easeOut",
        }}
      >
        <Typography
          variant="h1"
          sx={{
            fontSize: "8rem",
            fontWeight: "bold",
            color: "white",
            textShadow: "2px 2px 4px rgba(0,0,0,0.3)",
            fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
            letterSpacing: "0.1em",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            userSelect: "none",
            textAlign: "center",
          }}
        >
          <span
            style={{
              textAlign: "right",
              paddingRight: "0.2em",
            }}
          >
            rese
          </span>
          <Box
            component="span"
            sx={{
              position: "relative",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "1.2em",
              height: "1.2em",
              margin: "0em -0.3em -0.3em -0.3em",
            }}
          >
            <SearchIcon
              sx={{
                fontSize: "1em",
                color: "white",
                filter: "drop-shadow(2px 2px 4px rgba(0,0,0,0.3))",
              }}
            />
          </Box>
          <span
            style={{
              textAlign: "left",
              paddingLeft: "0.2em",
            }}
          >
            rch
          </span>
        </Typography>
      </motion.div>
    </Box>
  );
};

export default LandingPage;
