import { useState } from 'react';
import {
  Box, TextField, Typography, Alert, Chip, IconButton,
  Collapse, Paper, Link, InputAdornment, CircularProgress,
} from '@mui/material';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import type { WizardData } from '../../pages/SetupWizard';
import { validateKey } from '../../services/api';

interface Props {
  data: WizardData;
  update: (d: Partial<WizardData>) => void;
}

interface KeyConfig {
  field: keyof WizardData;
  label: string;
  required: boolean;
  signupUrl: string;
  signupLabel: string;
  guideSteps: string[];
  placeholder: string;
}

const KEY_CONFIGS: KeyConfig[] = [
  {
    field: 'openaiKey',
    label: 'OpenAI (GPT)',
    required: true,
    signupUrl: 'https://platform.openai.com/api-keys',
    signupLabel: 'Get API Key at OpenAI',
    placeholder: 'sk-proj-...',
    guideSteps: [
      '1. Go to platform.openai.com → sign in / sign up',
      '2. Click "API Keys" in the left sidebar',
      '3. Click "+ Create new secret key"',
      '4. Name it → Copy key → Paste here',
    ],
  },
  {
    field: 'pexelsKey',
    label: 'Pexels (Stock footage)',
    required: false,
    signupUrl: 'https://www.pexels.com/api/',
    signupLabel: 'Sign up for Pexels API (free)',
    placeholder: 'AGzUZ1lk...',
    guideSteps: [
      '1. Go to pexels.com/api → create a free account',
      '2. Fill out "I want to use Pexels API" form',
      '3. Go to pexels.com/api/new → create new API key',
      '4. Copy key → Paste here',
    ],
  },
  {
    field: 'elevenlabsKey',
    label: 'ElevenLabs (TTS)',
    required: false,
    signupUrl: 'https://elevenlabs.io/app/settings/api-keys',
    signupLabel: 'Get key at ElevenLabs',
    placeholder: 'xi-api-...',
    guideSteps: [
      '1. Go to elevenlabs.io → sign up (free tier: 10k chars/month)',
      '2. Go to Settings → API Keys',
      '3. Click "Create API Key"',
      '4. Copy → Paste here',
      'Not required — system uses free edge-tts by default',
    ],
  },
  {
    field: 'klingKey',
    label: 'Kling AI (Video generation)',
    required: false,
    signupUrl: 'https://klingai.com',
    signupLabel: 'Sign up at Kling AI',
    placeholder: 'kl-...',
    guideSteps: [
      '1. Go to klingai.com → sign up',
      '2. Go to API Keys section',
      '3. Create a new API key',
      '4. Copy → Paste here',
      'Enables AI-generated video clips (not just images)',
    ],
  },
  {
    field: 'runwayKey',
    label: 'RunwayML (Video generation)',
    required: false,
    signupUrl: 'https://runwayml.com',
    signupLabel: 'Sign up at RunwayML',
    placeholder: 'key_...',
    guideSteps: [
      '1. Go to runwayml.com → sign up',
      '2. Go to Account → API Keys',
      '3. Create API Key + Secret',
      '4. Paste both key and secret below',
      'Alternative to Kling for AI video clips',
    ],
  },
  {
    field: 'runwaySecret',
    label: 'RunwayML (API Secret)',
    required: false,
    signupUrl: 'https://runwayml.com',
    signupLabel: 'Get secret at RunwayML',
    placeholder: 'secret_...',
    guideSteps: [
      '1. Generated alongside the API key',
      '2. Keep this secret — do not share',
      '3. Both key + secret are required for Runway',
    ],
  },
];

export default function ApiKeyStep({ data, update }: Props) {
  const [expandedGuide, setExpandedGuide] = useState<string | null>(null);
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [validating, setValidating] = useState<Record<string, boolean>>({});
  const [validated, setValidated] = useState<Record<string, boolean>>({});

  const toggleGuide = (field: string) =>
    setExpandedGuide((prev) => (prev === field ? null : field));

  const toggleShow = (field: string) =>
    setShowKeys((prev) => ({ ...prev, [field]: !prev[field] }));

  const handleValidate = async (field: string, key: string) => {
    if (!key) return;
    setValidating((prev) => ({ ...prev, [field]: true }));
    try {
      await validateKey(field, key);
      setValidated((prev) => ({ ...prev, [field]: true }));
    } catch {
      setValidated((prev) => ({ ...prev, [field]: false }));
    }
    setValidating((prev) => ({ ...prev, [field]: false }));
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <VpnKeyIcon color="primary" /> API Keys & Services
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Enter your API keys or click the links to sign up. Detailed setup guides available for each service.
      </Typography>

      {KEY_CONFIGS.map((cfg) => {
        const value = data[cfg.field] as string;
        const isValid = validated[cfg.field as string];

        return (
          <Paper
            key={cfg.field}
            sx={{
              p: 2.5,
              bgcolor: 'rgba(15, 23, 42, 0.02)',
              borderRadius: 3,
              border: isValid
                ? '1px solid rgba(105,240,174,0.3)'
                : '1px solid rgba(15, 23, 42, 0.06)',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
              <Typography variant="subtitle1" fontWeight={600}>
                {cfg.label}
              </Typography>
              {cfg.required && (
                <Chip label="Required" size="small" color="warning" variant="outlined" />
              )}
              {!cfg.required && (
                <Chip label="Optional" size="small" variant="outlined"
                  sx={{ borderColor: 'rgba(255,255,255,0.15)' }} />
              )}
              {isValid && <CheckCircleIcon sx={{ color: 'success.main', ml: 'auto' }} />}
            </Box>

            <TextField
              placeholder={cfg.placeholder}
              value={value}
              onChange={(e) => update({ [cfg.field]: e.target.value })}
              fullWidth
              size="small"
              type={showKeys[cfg.field as string] ? 'text' : 'password'}
              InputProps={{
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton size="small" onClick={() => toggleShow(cfg.field as string)}>
                      {showKeys[cfg.field as string] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                    </IconButton>
                    {validating[cfg.field as string] ? (
                      <CircularProgress size={20} />
                    ) : null}
                  </InputAdornment>
                ),
              }}
            />

            <Box sx={{ mt: 1.5, display: 'flex', gap: 1, alignItems: 'center' }}>
              <Link
                href={cfg.signupUrl}
                target="_blank"
                sx={{
                  display: 'flex', alignItems: 'center', gap: 0.5,
                  fontSize: '0.85rem', color: 'primary.light',
                }}
              >
                <OpenInNewIcon sx={{ fontSize: 16 }} />
                {cfg.signupLabel}
              </Link>

              <Typography variant="body2" sx={{ mx: 0.5, color: 'text.secondary' }}>|</Typography>

              <Typography
                variant="body2"
                onClick={() => toggleGuide(cfg.field as string)}
                sx={{
                  cursor: 'pointer', color: 'text.secondary',
                  display: 'flex', alignItems: 'center', gap: 0.5,
                  '&:hover': { color: 'primary.light' },
                }}
              >
                Guide
                <ExpandMoreIcon
                  sx={{
                    fontSize: 18,
                    transform: expandedGuide === cfg.field ? 'rotate(180deg)' : 'none',
                    transition: 'transform 0.2s',
                  }}
                />
              </Typography>
            </Box>

            <Collapse in={expandedGuide === cfg.field}>
              <Alert severity="info" sx={{ mt: 1.5, borderRadius: 2 }}>
                {cfg.guideSteps.map((step, i) => (
                  <Typography key={i} variant="body2" sx={{ mb: 0.3 }}>
                    {step}
                  </Typography>
                ))}
              </Alert>
            </Collapse>
          </Paper>
        );
      })}
    </Box>
  );
}