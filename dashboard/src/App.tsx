import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, Container, Box, IconButton,
  Chip, Button, Fade,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import DashboardRoundedIcon from '@mui/icons-material/DashboardRounded';
import CalendarTodayRoundedIcon from '@mui/icons-material/CalendarTodayRounded';
import InsightsRoundedIcon from '@mui/icons-material/InsightsRounded';
import PowerRoundedIcon from '@mui/icons-material/PowerRounded';
import GitHubIcon from '@mui/icons-material/GitHub';
import SetupWizard from './pages/SetupWizard';
import Dashboard from './pages/Dashboard';
import JobDetail from './pages/JobDetail';
import ContentCalendar from './pages/ContentCalendar';
import Analytics from './pages/Analytics';
import OAuthConnect from './pages/OAuthConnect';

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Dashboard', Icon: DashboardRoundedIcon },
  { path: '/calendar', label: 'Calendar', Icon: CalendarTodayRoundedIcon },
  { path: '/analytics', label: 'Insights', Icon: InsightsRoundedIcon },
  { path: '/connections', label: 'Connect', Icon: PowerRoundedIcon },
];

export default function App() {
  const location = useLocation();

  return (
    <Box sx={{ minHeight: '100vh' }}>
      {/* AppBar */}
      <AppBar
        position="sticky"
        elevation={0}
        sx={{
          background: 'rgba(255, 255, 255, 0.85)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid rgba(15, 23, 42, 0.06)',
        }}
      >
        <Toolbar sx={{ gap: 1 }}>
          {/* Logo */}
          <Box sx={{
            width: 32, height: 32, borderRadius: '8px', mr: 1,
            background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '14px', fontWeight: 700, color: '#fff',
            boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
            transition: 'transform 0.3s ease, box-shadow 0.3s ease',
            '&:hover': { transform: 'scale(1.05)', boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)' },
          }}>
            A
          </Box>
          <Typography variant="h6" sx={{ fontWeight: 700, fontSize: '1rem', mr: 3, color: '#0F172A' }}>
            Agent Content Kit
          </Typography>

          {/* Nav */}
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {NAV_ITEMS.map(({ path, label, Icon }) => {
              const active = location.pathname === path;
              return (
                <Button
                  key={path}
                  href={path}
                  size="small"
                  startIcon={<Icon sx={{ fontSize: '18px !important' }} />}
                  sx={{
                    color: active ? '#6366F1' : '#64748B',
                    bgcolor: active ? alpha('#6366F1', 0.08) : 'transparent',
                    borderRadius: '8px', px: 1.5, fontSize: '0.8rem',
                    fontWeight: active ? 600 : 500,
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                      bgcolor: active ? alpha('#6366F1', 0.12) : alpha('#0F172A', 0.04),
                      color: active ? '#6366F1' : '#0F172A',
                      transform: 'translateY(-1px)',
                    },
                  }}
                >
                  {label}
                </Button>
              );
            })}
          </Box>

          <Box sx={{ flexGrow: 1 }} />
          <Chip
            label="v1.0"
            size="small"
            sx={{
              mr: 1, bgcolor: alpha('#6366F1', 0.08),
              color: '#6366F1', fontWeight: 600, height: 24, fontSize: '0.7rem',
              border: `1px solid ${alpha('#6366F1', 0.12)}`,
            }}
          />
          <IconButton
            href="https://github.com/vovuhuydeveloper/agent-content-kit"
            target="_blank"
            size="small"
            sx={{
              color: '#94A3B8',
              transition: 'all 0.2s ease',
              '&:hover': { color: '#0F172A', transform: 'rotate(15deg)' },
            }}
          >
            <GitHubIcon fontSize="small" />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Content with page transition */}
      <Fade in key={location.pathname} timeout={350}>
        <Container maxWidth="lg" sx={{ py: 4 }} className="page-enter">
          <Routes>
            <Route path="/" element={<Navigate to="/setup" replace />} />
            <Route path="/setup" element={<SetupWizard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/jobs/:jobId" element={<JobDetail />} />
            <Route path="/calendar" element={<ContentCalendar />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/connections" element={<OAuthConnect />} />
          </Routes>
        </Container>
      </Fade>
    </Box>
  );
}
