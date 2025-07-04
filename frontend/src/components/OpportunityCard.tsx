import React from "react";
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Chip,
  Button,
  Box,
} from "@mui/material";
import {
  School as SchoolIcon,
  Launch as LaunchIcon,
  Event as EventIcon,
  LocationOn as LocationIcon,
} from "@mui/icons-material";
import { Opportunity } from "../services/api";

interface OpportunityCardProps {
  opportunity: Opportunity;
}

export const OpportunityCard: React.FC<OpportunityCardProps> = ({
  opportunity,
}) => {
  const formatDate = (dateString?: string) => {
    if (!dateString) return null;
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  const truncateDescription = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + "...";
  };

  const getCategoryColor = (category?: string) => {
    if (!category) return "default";
    switch (category.toLowerCase()) {
      case "research":
        return "primary";
      case "internship":
        return "secondary";
      case "fellowship":
        return "success";
      case "graduate":
        return "info";
      case "undergraduate":
        return "warning";
      default:
        return "default";
    }
  };

  const getDeadlineColor = (deadline?: string) => {
    if (!deadline) return "text.secondary";

    try {
      const deadlineDate = new Date(deadline);
      const now = new Date();
      const daysUntilDeadline = Math.ceil(
        (deadlineDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)
      );

      if (daysUntilDeadline < 0) return "error.main";
      if (daysUntilDeadline <= 7) return "error.main";
      if (daysUntilDeadline <= 30) return "warning.main";
      return "success.main";
    } catch {
      return "text.secondary";
    }
  };

  return (
    <Card
      sx={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        opacity: opportunity.is_active ? 1 : 0.7,
        borderLeft: opportunity.is_active
          ? "4px solid #1976d2"
          : "4px solid #757575",
      }}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            mb: 2,
          }}
        >
          <Typography variant="h6" component="h3" sx={{ flexGrow: 1, mr: 1 }}>
            {opportunity.title}
          </Typography>
          {opportunity.category && (
            <Chip
              label={opportunity.category}
              color={getCategoryColor(opportunity.category) as any}
              size="small"
            />
          )}
          {!opportunity.is_active && (
            <Chip
              label="Inactive"
              size="small"
              color="default"
              sx={{ ml: 1 }}
            />
          )}
        </Box>

        {opportunity.department && (
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <SchoolIcon sx={{ mr: 1, fontSize: 16, color: "text.secondary" }} />
            <Typography variant="body2" color="text.secondary">
              {opportunity.department}
            </Typography>
          </Box>
        )}

        {opportunity.location && (
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <LocationIcon
              sx={{ mr: 1, fontSize: 16, color: "text.secondary" }}
            />
            <Typography variant="body2" color="text.secondary">
              {opportunity.location}
            </Typography>
          </Box>
        )}

        {opportunity.deadline && (
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <EventIcon
              sx={{
                mr: 1,
                fontSize: 16,
                color: getDeadlineColor(opportunity.deadline),
              }}
            />
            <Typography
              variant="body2"
              color={getDeadlineColor(opportunity.deadline)}
            >
              Deadline: {formatDate(opportunity.deadline)}
            </Typography>
          </Box>
        )}

        {opportunity.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {truncateDescription(opportunity.description)}
          </Typography>
        )}

        {opportunity.requirements && (
          <Box sx={{ mb: 2 }}>
            <Typography
              variant="caption"
              color="text.secondary"
              display="block"
              gutterBottom
            >
              Requirements:
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ fontSize: "0.875rem" }}
            >
              {truncateDescription(opportunity.requirements, 150)}
            </Typography>
          </Box>
        )}
      </CardContent>

      <CardActions sx={{ px: 2, pb: 2 }}>
        {opportunity.url && (
          <Button
            size="small"
            color="primary"
            variant="contained"
            startIcon={<LaunchIcon />}
            href={opportunity.url}
            target="_blank"
            rel="noopener noreferrer"
            fullWidth
          >
            View Details
          </Button>
        )}
      </CardActions>
    </Card>
  );
};

export default OpportunityCard;
