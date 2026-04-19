import { useState, useEffect } from 'react';
import {
  Box, Typography, Paper, Chip, Alert, Button, CircularProgress, Link,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import RadioButtonUncheckedIcon from '@mui/icons-material/RadioButtonUnchecked';
import ShareRoundedIcon from '@mui/icons-material/ShareRounded';
import FolderRoundedIcon from '@mui/icons-material/FolderRounded';
import OpenInBrowserRoundedIcon from '@mui/icons-material/OpenInBrowserRounded';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import api from '../../services/api';
import type { WizardData } from '../../pages/SetupWizard';

interface Props {
  data: WizardData;
  update: (d: Partial<WizardData>) => void;
}

const PLATFORMS = [
  {
    id: 'tiktok',
    label: 'TikTok',
    initial: 'Tk',
    color: '#25F4EE',
    desc: 'Short video 9:16, max 10 min',
  },
  {
    id: 'youtube',
    label: 'YouTube Shorts',
    initial: 'YT',
    color: '#FF0000',
    desc: 'Shorts 9:16, max 60s',
  },
  {
    id: 'facebook',
    label: 'Facebook Reels',
    initial: 'FB',
    color: '#1877F2',
    desc: 'Reels 9:16, max 90s',
  },
];

export default function PlatformStep({ data, update }: Props) {
  const [connecting, setConnecting] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<Record<string, boolean>>({});
  const [loginAlert, setLoginAlert] = useState<string | null>(null);

  // Fetch browser session status
  const fetchSessionStatus = async () => {
    try {
      const res = await api.get('/browser-session/status');
      const statuses: Record<string, boolean> = {};
      res.data.forEach((s: { platform: string; connected: boolean }) => {
        statuses[s.platform] = s.connected;
      });
      setSessionStatus(statuses);

      // Auto-clear login alert if connected
      if (loginAlert && statuses[loginAlert]) {
        setLoginAlert(null);
      }
    } catch (err) {
      console.error('Failed to check session:', err);
    }
  };

  useEffect(() => {
    fetchSessionStatus();
    // Poll every 5s to detect login completion
    const timer = setInterval(fetchSessionStatus, 5000);
    return () => clearInterval(timer);
  }, [loginAlert]);

  const handleConnect = async (platformId: string) => {
    setConnecting(platformId);
    try {
      const res = await api.post(`/browser-session/${platformId}/connect`);
      if (res.data.status === 'already_connected') {
        fetchSessionStatus();
      } else {
        setLoginAlert(platformId);
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to open browser');
    }
    setConnecting(null);
  };

  const toggle = (id: string) => {
    const platforms = data.platforms.includes(id)
      ? data.platforms.filter((p) => p !== id)
      : [...data.platforms, id];
    update({ platforms });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ShareRoundedIcon color="primary" /> Target Platforms
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Select where you want to publish. Click "Connect" to login via Chrome browser.
      </Typography>

      {/* Login alert */}
      {loginAlert && (
        <Alert severity="info" sx={{ borderRadius: 3 }} onClose={() => setLoginAlert(null)}>
          Chrome đã mở — login <strong>{loginAlert}</strong> rồi đóng cửa sổ Chrome.
          Status sẽ tự cập nhật khi hoàn tất.
        </Alert>
      )}

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
        {PLATFORMS.map((p) => {
          const selected = data.platforms.includes(p.id);
          const isConnected = sessionStatus[p.id] || false;
          const isConnecting = connecting === p.id;

          return (
            <Paper
              key={p.id}
              sx={{
                borderRadius: 3,
                border: selected
                  ? `2px solid ${p.color}40`
                  : '2px solid transparent',
                bgcolor: selected
                  ? `${p.color}08`
                  : alpha('#94A3B8', 0.04),
                transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                overflow: 'hidden',
                '&:hover': {
                  bgcolor: `${p.color}12`,
                },
              }}
            >
              {/* Clickable header — select/deselect */}
              <Box
                onClick={() => toggle(p.id)}
                sx={{ p: 2.5, cursor: 'pointer', '&:hover': { transform: 'translateY(-1px)' }, transition: 'transform 0.2s' }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Box sx={{
                    width: 36, height: 36, borderRadius: '8px', fontSize: '0.75rem',
                    fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    bgcolor: `${p.color}18`, color: p.color,
                  }}>{p.initial}</Box>
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="subtitle1" fontWeight={600}>
                      {p.label}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {p.desc}
                    </Typography>
                  </Box>
                  {selected ? (
                    <CheckCircleIcon sx={{ color: p.color }} />
                  ) : (
                    <RadioButtonUncheckedIcon sx={{ color: alpha('#94A3B8', 0.3) }} />
                  )}
                </Box>
              </Box>

              {/* Connection status + Connect button — when selected */}
              {selected && (
                <Box sx={{ px: 2.5, pb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                  {isConnected ? (
                    <Chip
                      icon={<CheckCircleOutlineIcon />}
                      label="Connected"
                      color="success"
                      size="small"
                      variant="outlined"
                      sx={{ fontWeight: 600 }}
                    />
                  ) : (
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={(e) => { e.stopPropagation(); handleConnect(p.id); }}
                      disabled={isConnecting}
                      startIcon={isConnecting
                        ? <CircularProgress size={14} />
                        : <OpenInBrowserRoundedIcon />
                      }
                      sx={{
                        textTransform: 'none',
                        borderColor: alpha(p.color, 0.3),
                        color: p.color,
                        '&:hover': { borderColor: p.color, bgcolor: alpha(p.color, 0.05) },
                      }}
                    >
                      {isConnecting ? 'Opening...' : 'Connect'}
                    </Button>
                  )}
                </Box>
              )}
            </Paper>
          );
        })}
      </Box>

      {data.platforms.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mr: 1 }}>
            Selected:
          </Typography>
          {data.platforms.map((p) => (
            <Chip
              key={p}
              label={PLATFORMS.find((x) => x.id === p)?.label ?? p}
              size="small"
              onDelete={() => toggle(p)}
              sx={{ bgcolor: alpha('#6366F1', 0.06) }}
            />
          ))}
        </Box>
      )}

      <Alert
        severity="info"
        icon={<FolderRoundedIcon />}
        sx={{ borderRadius: 3 }}
      >
        <Typography variant="body2" fontWeight={500}>
          Videos are always saved locally
        </Typography>
        <Typography variant="caption" color="text.secondary">
          All generated videos, scripts, and thumbnails are saved to <code>data/jobs/{'<job_id>'}/</code> regardless
          of platform connections. You can connect accounts later from the{' '}
          <Link href="/connections" sx={{ fontWeight: 600 }}>Connect</Link> page.
        </Typography>
      </Alert>
    </Box>
  );
}
