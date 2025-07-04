import React, { useState, useEffect } from "react";
import { Box, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { Search as SearchIcon } from "@mui/icons-material";
import { motion, AnimatePresence } from "framer-motion";

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [startAnimation, setStartAnimation] = useState(false);

  useEffect(() => {
    // Start animation after 1 second
    const timer = setTimeout(() => {
      setStartAnimation(true);
    }, 1000);

    // Navigate to home page after animation completes
    const navigationTimer = setTimeout(() => {
      navigate("/home");
    }, 4000);

    return () => {
      clearTimeout(timer);
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
        background: "linear-gradient(135deg, #8C1515 0%, #651010 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
        zIndex: 9999,
      }}
    >
      {/* Main Logo Container */}
      <motion.div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        animate={
          startAnimation
            ? {
                scale: [1, 1.1, 1.3, 2, 3, 5, 8, 12, 18, 25],
                opacity: [1, 1, 0.95, 0.85, 0.7, 0.5, 0.3, 0.15, 0.05, 0],
              }
            : {}
        }
        transition={{
          duration: 3,
          ease: "easeInOut",
          times: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1],
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
            width: "100%",
            textAlign: "center",
          }}
        >
          <span
            style={{ flex: "1", textAlign: "right", paddingRight: "0.5em" }}
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
              flex: "0 0 auto",
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
          <span style={{ flex: "1", textAlign: "left", paddingLeft: "0.5em" }}>
            rch
          </span>
        </Typography>
      </motion.div>

      {/* Circular Reveal Effect */}
      <motion.div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "40px",
          height: "40px",
          borderRadius: "50%",
          overflow: "hidden",
          background: "linear-gradient(135deg, #FAFAFA 0%, #F5F5F5 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
        animate={
          startAnimation
            ? {
                width: [
                  "40px",
                  "60px",
                  "100px",
                  "160px",
                  "250px",
                  "400px",
                  "600px",
                  "900px",
                  "1400px",
                  "2000px",
                  "300vw",
                ],
                height: [
                  "40px",
                  "60px",
                  "100px",
                  "160px",
                  "250px",
                  "400px",
                  "600px",
                  "900px",
                  "1400px",
                  "2000px",
                  "300vh",
                ],
                opacity: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
              }
            : {}
        }
        transition={{
          duration: 3,
          ease: "easeInOut",
          times: [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
        }}
      >
        {/* Preview of home page content */}
        <motion.div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            opacity: 0,
          }}
          animate={
            startAnimation
              ? {
                  scale: [0.05, 0.1, 0.15, 0.2],
                  opacity: [0, 0.3, 0.6, 0.8],
                }
              : {}
          }
          transition={{
            duration: 2.5,
            ease: "easeOut",
            delay: 1,
            times: [0, 0.33, 0.66, 1],
          }}
        >
          <Typography
            variant="h4"
            sx={{
              color: "#8C1515",
              fontWeight: "bold",
              textAlign: "center",
              mb: 2,
              whiteSpace: "nowrap",
            }}
          >
            Stanford Research
          </Typography>
          <Typography
            variant="h6"
            sx={{
              color: "#333",
              textAlign: "center",
              whiteSpace: "nowrap",
            }}
          >
            Opportunities
          </Typography>
        </motion.div>
      </motion.div>
    </Box>
  );
};

export default LandingPage;
