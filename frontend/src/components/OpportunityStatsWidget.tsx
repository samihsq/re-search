import React, { useState, useEffect } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Chip,
  CircularProgress,
  Alert,
} from "@mui/material";
import {
  TrendingUp as TrendingUpIcon,
  NewReleases as NewIcon,
  AttachMoney as FundingIcon,
  School as TotalIcon,
} from "@mui/icons-material";
import { apiService } from "../services/api";

interface OpportunityStats {
  total_active: number;
  recent_new_opportunities: number;
  funded_opportunities: number;
  status_breakdown: { [key: string]: number };
  top_departments: Array<{ department: string; count: number }>;
}

const OpportunityStatsWidget: React.FC = () => {
  const [stats, setStats] = useState<OpportunityStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await apiService.getOpportunityStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError("Failed to load opportunity statistics");
        console.error("Error fetching stats:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    // Refresh stats every 5 minutes
    const interval = setInterval(fetchStats, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent sx={{ textAlign: "center", py: 4 }}>
          <CircularProgress />
          <Typography variant="body2" sx={{ mt: 2 }}>
            Loading statistics...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!stats) {
    return null;
  }

  const StatCard: React.FC<{
    title: string;
    value: number;
    icon: React.ReactNode;
    color: string;
    subtitle?: string;
  }> = ({ title, value, icon, color, subtitle }) => (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", mb: 1 }}>
          <Box sx={{ color, mr: 1 }}>{icon}</Box>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
        </Box>
        <Typography
          variant="h4"
          component="p"
          sx={{ fontWeight: "bold", color }}
        >
          {value.toLocaleString()}
        </Typography>
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Box>
      <Typography variant="h5" component="h2" sx={{ mb: 3 }}>
        📊 Opportunity Statistics
      </Typography>

      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Active"
            value={stats.total_active}
            icon={<TotalIcon />}
            color="primary.main"
            subtitle="All active opportunities"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="New This Week"
            value={stats.recent_new_opportunities}
            icon={<NewIcon />}
            color="success.main"
            subtitle="Discovered in last 7 days"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="With Funding"
            value={stats.funded_opportunities}
            icon={<FundingIcon />}
            color="warning.main"
            subtitle="Opportunities with stipends"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Trending Up"
            value={Math.round(
              (stats.recent_new_opportunities / stats.total_active) * 100
            )}
            icon={<TrendingUpIcon />}
            color="info.main"
            subtitle="% new this week"
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h3" sx={{ mb: 2 }}>
                Opportunity Status
              </Typography>
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                {Object.entries(stats.status_breakdown).map(
                  ([status, count]) => {
                    const getStatusColor = (status: string) => {
                      switch (status) {
                        case "new":
                          return "primary";
                        case "active":
                          return "success";
                        case "missing":
                          return "warning";
                        case "removed":
                          return "error";
                        default:
                          return "default";
                      }
                    };

                    return (
                      <Chip
                        key={status}
                        label={`${status}: ${count}`}
                        color={getStatusColor(status) as any}
                        variant="outlined"
                      />
                    );
                  }
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h3" sx={{ mb: 2 }}>
                Top Departments
              </Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
                {stats.top_departments.slice(0, 5).map((dept, index) => (
                  <Box
                    key={dept.department}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      py: 0.5,
                    }}
                  >
                    <Typography variant="body2">
                      {index + 1}. {dept.department}
                    </Typography>
                    <Chip
                      label={dept.count}
                      size="small"
                      color="primary"
                      variant="outlined"
                    />
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OpportunityStatsWidget;
