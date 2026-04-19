import { useState, useEffect } from 'react';
import {
  Box, TextField, Typography, Button, Alert, Paper,
  Collapse, CircularProgress, Chip, Link,
} from '@mui/material';
import { alpha } from '@mui/material/styles';
import TelegramIcon from '@mui/icons-material/Telegram';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import PersonRoundedIcon from '@mui/icons-material/PersonRounded';
import type { WizardData } from '../../pages/SetupWizard';
import { testTelegramBot, detectTelegramChat, getConfig } from '../../services/api';

interface Props {
  data: WizardData;
  update: (d: Partial<WizardData>) => void;
}

export default function TelegramStep({ data, update }: Props) {
  const [showGuide, setShowGuide] = useState(false);
  const [detecting, setDetecting] = useState(false);
  const [detected, setDetected] = useState<{ name: string; chatId: string } | null>(null);
  const [detectError, setDetectError] = useState('');
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);

  // Auto-load saved token from backend on mount
  useEffect(() => {
    if (!data.telegramToken) {
      getConfig().then((cfg) => {
        const savedToken = cfg.telegram_bot_token || '';
        const savedChatId = cfg.telegram_chat_id || '';
        // Only use if it's a real token (not masked "****")
        if (savedToken && !savedToken.includes('****')) {
          update({ telegramToken: savedToken, telegramChatId: savedChatId });
        }
      }).catch(() => { /* ignore */ });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDetect = async () => {
    if (!data.telegramToken) return;
    setDetecting(true);
    setDetectError('');
    setDetected(null);
    try {
      const res = await detectTelegramChat(data.telegramToken);
      if (res.found) {
        setDetected({ name: res.name, chatId: res.chat_id });
        update({ telegramChatId: res.chat_id });
      } else {
        setDetectError(res.message || 'No /start message found. Send /start to your bot and try again.');
      }
    } catch {
      setDetectError('Failed to connect. Check your bot token.');
    }
    setDetecting(false);
  };

  const handleTest = async () => {
    if (!data.telegramToken || !data.telegramChatId) return;
    setTesting(true);
    setTestResult(null);
    try {
      await testTelegramBot(data.telegramToken, data.telegramChatId);
      setTestResult('success');
    } catch {
      setTestResult('error');
    }
    setTesting(false);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <TelegramIcon color="primary" /> Telegram Bot
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Connect a Telegram bot to receive notifications when videos are ready and approve uploads directly.
      </Typography>

      {/* Step 1: Bot Token */}
      <Paper sx={{ p: 2.5, bgcolor: 'rgba(15, 23, 42, 0.02)', borderRadius: 3 }}>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip label="1" size="small" color="primary" sx={{ width: 24, height: 24, '& .MuiChip-label': { px: 0 } }} />
          Paste your Bot Token
        </Typography>
        <TextField
          label="Bot Token"
          placeholder="123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw"
          value={data.telegramToken}
          onChange={(e) => {
            update({ telegramToken: e.target.value });
            setDetected(null);
            setDetectError('');
            setTestResult(null);
          }}
          fullWidth
          size="small"
        />
      </Paper>

      {/* Step 2: Auto-detect Chat ID */}
      <Paper sx={{
        p: 2.5, borderRadius: 3,
        bgcolor: detected ? alpha('#10B981', 0.04) : 'rgba(15, 23, 42, 0.02)',
        border: detected ? '1px solid' : undefined,
        borderColor: detected ? alpha('#10B981', 0.2) : undefined,
        transition: 'all 0.3s ease',
      }}>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
          <Chip label="2" size="small" color="primary" sx={{ width: 24, height: 24, '& .MuiChip-label': { px: 0 } }} />
          Connect your account
        </Typography>

        {!detected ? (
          <>
            <Alert severity="info" sx={{ borderRadius: 2, mb: 2 }}>
              <Typography variant="body2">
                1. Open your bot in Telegram and send <strong>/start</strong><br />
                2. Come back here and click the button below
              </Typography>
            </Alert>

            <Button
              variant="contained"
              onClick={handleDetect}
              disabled={detecting || !data.telegramToken}
              startIcon={detecting ? <CircularProgress size={16} /> : <SearchRoundedIcon />}
              sx={{ textTransform: 'none' }}
            >
              {detecting ? 'Searching...' : 'Detect my Chat ID'}
            </Button>

            {detectError && (
              <Alert severity="warning" sx={{ mt: 2, borderRadius: 2 }}>
                {detectError}
              </Alert>
            )}
          </>
        ) : (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{
              width: 40, height: 40, borderRadius: '50%',
              bgcolor: alpha('#10B981', 0.1), display: 'flex',
              alignItems: 'center', justifyContent: 'center',
            }}>
              <PersonRoundedIcon sx={{ color: '#10B981' }} />
            </Box>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="subtitle2" fontWeight={600}>{detected.name}</Typography>
              <Typography variant="caption" color="text.secondary">Chat ID: {detected.chatId}</Typography>
            </Box>
            <Chip icon={<CheckCircleIcon />} label="Connected" color="success" size="small" />
          </Box>
        )}
      </Paper>

      {/* Optional: Manual + Test */}
      {data.telegramChatId && !detected && (
        <Paper sx={{ p: 2.5, bgcolor: 'rgba(15, 23, 42, 0.02)', borderRadius: 3 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            Or enter Chat ID manually:
          </Typography>
          <TextField
            label="Chat ID"
            placeholder="1975438398"
            value={data.telegramChatId}
            onChange={(e) => update({ telegramChatId: e.target.value })}
            fullWidth
            size="small"
          />
        </Paper>
      )}

      {data.telegramChatId && (
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button
            variant="outlined"
            size="small"
            onClick={handleTest}
            disabled={testing || !data.telegramToken || !data.telegramChatId}
            startIcon={testing ? <CircularProgress size={16} /> : <TelegramIcon />}
          >
            Send test message
          </Button>
          {testResult === 'success' && (
            <Chip icon={<CheckCircleIcon />} label="Message sent!" color="success" size="small" />
          )}
          {testResult === 'error' && (
            <Chip label="Failed — check token & Chat ID" color="error" size="small" />
          )}
        </Box>
      )}

      {/* Guide */}
      <Typography
        variant="body2"
        onClick={() => setShowGuide(!showGuide)}
        sx={{
          cursor: 'pointer', color: 'primary.light',
          display: 'flex', alignItems: 'center', gap: 0.5,
          '&:hover': { color: 'primary.main' },
        }}
      >
        How to create a Telegram Bot
        <ExpandMoreIcon
          sx={{
            fontSize: 18,
            transform: showGuide ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.2s',
          }}
        />
      </Typography>

      <Collapse in={showGuide}>
        <Alert severity="info" sx={{ borderRadius: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
            Create a Bot Token:
          </Typography>
          <Typography variant="body2">
            1. Open Telegram → search for{' '}
            <Link href="https://t.me/BotFather" target="_blank">@BotFather</Link>
          </Typography>
          <Typography variant="body2">2. Send /newbot command</Typography>
          <Typography variant="body2">3. Name your bot → receive the token</Typography>
          <Typography variant="body2">4. Copy the token → paste it above</Typography>
        </Alert>
      </Collapse>

      <Alert severity="success" sx={{ borderRadius: 3 }}>
        Once connected, the bot will notify you when videos are ready. Approve or reject directly from Telegram.
      </Alert>
    </Box>
  );
}
