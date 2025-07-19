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
  AttachMoney as MoneyIcon,
  NewReleases as NewIcon,
  VisibilityOff as MissingIcon,
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

    const date = new Date(dateString);

    // Check if the date is valid
    if (isNaN(date.getTime())) {
      // If date is invalid, return the original string
      return dateString;
    }

    try {
      return date.toLocaleDateString();
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

    const deadlineDate = new Date(deadline);

    // Check if the date is valid
    if (isNaN(deadlineDate.getTime())) {
      // If date is invalid, return neutral color
      return "text.secondary";
    }

    try {
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

  const getStatusIndicator = (status?: string) => {
    if (!status) return null;

    switch (status) {
      case "new":
        return (
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <NewIcon sx={{ mr: 1, fontSize: 16, color: "primary.main" }} />
            <Typography
              variant="body2"
              color="primary.main"
              sx={{ fontWeight: "medium" }}
            >
              New Opportunity
            </Typography>
          </Box>
        );
      case "missing":
        return (
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <MissingIcon sx={{ mr: 1, fontSize: 16, color: "text.disabled" }} />
            <Typography
              variant="body2"
              color="text.disabled"
              sx={{ fontSize: "0.75rem" }}
            >
              Not found in recent scrape
            </Typography>
          </Box>
        );
      default:
        return null;
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
          ? "4px solid#248910"
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

        {getStatusIndicator(opportunity.status)}

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

        {opportunity.funding_amount && (
          <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
            <MoneyIcon sx={{ mr: 1, fontSize: 16, color: "success.main" }} />
            <Typography
              variant="body2"
              color="success.main"
              sx={{ fontWeight: "medium" }}
            >
              Funding: {opportunity.funding_amount}
            </Typography>
          </Box>
        )}

        {opportunity.description && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {truncateDescription(opportunity.description)}
          </Typography>
        )}

        {opportunity.tags && opportunity.tags.length > 0 && (
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 2 }}>
            {opportunity.tags.map((tag, index) => (
              <Chip key={index} label={tag} size="small" />
            ))}
          </Box>
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
