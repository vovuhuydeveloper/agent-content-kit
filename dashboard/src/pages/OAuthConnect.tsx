import { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Chip, CircularProgress, Button, Grow, Alert,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import CheckCircleRoundedIcon from '@mui/icons-material/CheckCircleRounded';
import RadioButtonUncheckedRoundedIcon from '@mui/icons-material/RadioButtonUncheckedRounded';
import OpenInBrowserRoundedIcon from '@mui/icons-material/OpenInBrowserRounded';
import api from '../services/api';

// SVG icons for platforms
function YouTubeIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M23.5 6.19a3.02 3.02 0 00-2.12-2.14C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.38.55A3.02 3.02 0 00.5 6.19 31.57 31.57 0 000 12a31.57 31.57 0 00.5 5.81 3.02 3.02 0 002.12 2.14c1.88.55 9.38.55 9.38.55s7.5 0 9.38-.55a3.02 3.02 0 002.12-2.14A31.57 31.57 0 0024 12a31.57 31.57 0 00-.5-5.81z" fill="#FF0000"/>
      <path d="M9.55 15.57V8.43L15.82 12l-6.27 3.57z" fill="#fff"/>
    </svg>
  );
}

function TikTokIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.88-2.89 2.89 2.89 0 012.88-2.89c.28 0 .56.04.82.12V9.01a6.34 6.34 0 00-.82-.05A6.34 6.34 0 003.15 15.3a6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.34-6.34V9.44a8.16 8.16 0 004.76 1.52V7.51a4.83 4.83 0 01-1-.82z" fill="#25F4EE"/>
      <path d="M17.59 4.69a4.83 4.83 0 01-3.77-4.25V0h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.88-2.89 2.89 2.89 0 012.88-2.89c.28 0 .56.04.82.12V7.01a6.34 6.34 0 00-.82-.05A6.34 6.34 0 001.15 13.3a6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.34-6.34V7.44a8.16 8.16 0 004.76 1.52V5.51a4.83 4.83 0 01-1-.82z" fill="#FE2C55"/>
    </svg>
  );
}

function FacebookIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
      <path d="M24 12c0-6.627-5.373-12-12-12S0 5.373 0 12c0 5.99 4.388 10.954 10.125 11.854V15.47H7.078V12h3.047V9.356c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.875V12h3.328l-.532 3.47h-2.796v8.385C19.612 22.954 24 17.99 24 12z" fill="#1877F2"/>
    </svg>
  );
}

const PLATFORM_ICONS: Record<string, React.ReactNode> = {
  youtube: <YouTubeIcon />,
  tiktok: <TikTokIcon />,
  facebook: <FacebookIcon />,
};

const PLATFORM_COLORS: Record<string, string> = {
  youtube: '#FF0000',
  tiktok: '#25F4EE',
  facebook: '#1877F2',
};

const PLATFORMS = [
  { key: 'youtube', name: 'YouTube', description: 'Upload videos as Private to your channel' },
  { key: 'tiktok', name: 'TikTok', description: 'Publish short videos to TikTok' },
  { key: 'facebook', name: 'Facebook', description: 'Post videos as Reels to Facebook' },
];

interface BrowserSessionStatus {
  platform: string;
  connected: boolean;
}

export default function OAuthConnect() {
  const [statuses, setStatuses] = useState<BrowserSessionStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [loginAlert, setLoginAlert] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await api.get('/browser-session/status');
      setStatuses(res.data);
    } catch (err) {
      console.error('Failed to load session status:', err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchStatus();
    // Poll every 5s to detect login completion
    const timer = setInterval(fetchStatus, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleConnect = async (platform: string) => {
    setConnecting(platform);
    setLoginAlert(null);
    try {
      const res = await api.post(`/browser-session/${platform}/connect`);
      if (res.data.status === 'already_connected') {
        setLoginAlert(null);
        fetchStatus();
      } else {
        setLoginAlert(platform);
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to open browser');
    }
    setConnecting(null);
  };

  const getStatus = (platform: string): boolean => {
    return statuses.find(s => s.platform === platform)?.connected || false;
  };

  const connectedCount = statuses.filter(s => s.connected).length;

  if (loading) {
    return <Box sx={{ textAlign: 'center', py: 10 }}><CircularProgress size={32} sx={{ color: '#6366F1' }} /></Box>;
  }

  return (
    <Box>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ mb: 0.5 }}>Connections</Typography>
        <Typography variant="body2" color="text.secondary">
          Platform sessions for auto-publishing • {connectedCount}/{PLATFORMS.length} connected
        </Typography>
      </Box>

      {/* Login alert */}
      {loginAlert && (
        <Alert
          severity="info"
          sx={{ mb: 2, borderRadius: 3 }}
          onClose={() => setLoginAlert(null)}
        >
          Chrome đã mở — login <strong>{loginAlert}</strong> rồi đóng cửa sổ Chrome. Status sẽ tự cập nhật.
        </Alert>
      )}

      {/* Platform Cards */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {PLATFORMS.map((p, idx) => {
          const isConnected = getStatus(p.key);
          const color = PLATFORM_COLORS[p.key];

          return (
            <Grow in timeout={300 + idx * 100} key={p.key}>
            <Paper
              sx={{
                p: 2.5, display: 'flex', alignItems: 'center', gap: 2,
                borderRadius: 3,
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                borderLeft: isConnected ? `3px solid ${color}` : `3px solid transparent`,
                '&:hover': {
                  transform: 'translateY(-2px)',
                  boxShadow: `0 8px 24px ${alpha(color, 0.1)}`,
                },
              }}
            >
              {/* Platform icon */}
              <Box sx={{
                width: 44, height: 44, borderRadius: '11px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                bgcolor: alpha(color, 0.08),
              }}>
                {PLATFORM_ICONS[p.key]}
              </Box>

              {/* Info */}
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="subtitle1" fontWeight={600}>{p.name}</Typography>
                <Typography variant="caption" color="text.secondary">{p.description}</Typography>
              </Box>

              {/* Status + Action */}
              {isConnected ? (
                <Chip
                  icon={<CheckCircleRoundedIcon sx={{ fontSize: '14px !important' }} />}
                  label="Connected"
                  size="small"
                  color="success"
                  variant="outlined"
                  sx={{ fontWeight: 500 }}
                />
              ) : (
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => handleConnect(p.key)}
                  disabled={connecting === p.key}
                  startIcon={connecting === p.key
                    ? <CircularProgress size={14} />
                    : <OpenInBrowserRoundedIcon />
                  }
                  sx={{
                    borderColor: alpha(color, 0.3),
                    color,
                    '&:hover': { borderColor: color, bgcolor: alpha(color, 0.05) },
                  }}
                >
                  Connect
                </Button>
              )}
            </Paper>
            </Grow>
          );
        })}
      </Box>
    </Box>
  );
}
