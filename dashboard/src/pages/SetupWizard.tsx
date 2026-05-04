import { useState, useEffect } from 'react';
import {
  Box, Stepper, Step, StepLabel, Button, Typography, Paper,
  Fade, useTheme, CircularProgress,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';

import { useNavigate } from 'react-router-dom';

import SourceStep from '../components/wizard/SourceStep';
import CompetitorStep from '../components/wizard/CompetitorStep';
import AssetStep from '../components/wizard/AssetStep';
import ApiKeyStep from '../components/wizard/ApiKeyStep';
import PlatformStep from '../components/wizard/PlatformStep';
import TelegramStep from '../components/wizard/TelegramStep';
import { createJob, saveConfig, getConfig } from '../services/api';

const STEPS = [
  'Content Source',
  'Competitors',
  'Assets',
  'API Keys',
  'Platforms',
  'Telegram',
];

export interface WizardData {
  sourceUrl: string;
  sourceDoc: File | null;
  niche: string;
  language: string;
  videoCount: number;
  aspectRatio: string;
  scheduleEnabled: boolean;
  scheduleFrequency: string;
  scheduleTime: string;
  competitorUrls: string[];
  competitorDoc: File | null;
  characterFiles: File[];
  openaiKey: string;
  pexelsKey: string;
  elevenlabsKey: string;
  platforms: string[];
  oauthCreds: Record<string, { clientId: string; clientSecret: string }>;
  telegramToken: string;
  telegramChatId: string;
}

const initialData: WizardData = {
  sourceUrl: '',
  sourceDoc: null,
  niche: '',
  language: 'en',
  videoCount: 1,
  aspectRatio: '9:16',
  scheduleEnabled: false,
  scheduleFrequency: 'daily',
  scheduleTime: '09:00',
  competitorUrls: [''],
  competitorDoc: null,
  characterFiles: [],
  openaiKey: '',
  pexelsKey: '',
  elevenlabsKey: '',
  platforms: ['tiktok'],
  oauthCreds: {},
  telegramToken: '',
  telegramChatId: '',
};

export default function SetupWizard() {
  const [step, setStep] = useState(() => {
    const saved = localStorage.getItem('wizard_step');
    return saved ? parseInt(saved, 10) : 0;
  });
  const [data, setData] = useState<WizardData>(() => {
    try {
      const saved = localStorage.getItem('wizard_data');
      if (saved) {
        const parsed = JSON.parse(saved);
        // File objects can't be serialized — restore defaults
        return { ...initialData, ...parsed, sourceDoc: null, competitorDoc: null, characterFiles: [] };
      }
    } catch { /* ignore */ }
    return initialData;
  });
  const [submitting, setSubmitting] = useState(false);


  // Load saved API keys from backend on mount
  useEffect(() => {
    getConfig().then((cfg) => {
      const updates: Partial<WizardData> = {};
      // Only fill if user hasn't already typed something
      if (!data.openaiKey && cfg.openai_api_key && !cfg.openai_api_key.includes('****')) {
        updates.openaiKey = cfg.openai_api_key;
      }
      if (!data.pexelsKey && cfg.pexels_api_key && !cfg.pexels_api_key.includes('****')) {
        updates.pexelsKey = cfg.pexels_api_key;
      }
      if (!data.elevenlabsKey && cfg.elevenlabs_api_key && !cfg.elevenlabs_api_key.includes('****')) {
        updates.elevenlabsKey = cfg.elevenlabs_api_key;
      }
      if (!data.telegramToken && cfg.telegram_bot_token) {
        updates.telegramToken = cfg.telegram_bot_token;
      }
      if (!data.telegramChatId && cfg.telegram_chat_id) {
        updates.telegramChatId = cfg.telegram_chat_id;
      }
      if (Object.keys(updates).length > 0) {
        update(updates);
      }
    }).catch(() => { /* server not ready yet */ });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navigate = useNavigate();
  const theme = useTheme();

  // Persist step & data to localStorage
  const updateStep = (newStep: number) => {
    setStep(newStep);
    localStorage.setItem('wizard_step', String(newStep));
  };

  const update = (partial: Partial<WizardData>) =>
    setData((prev) => {
      const next = { ...prev, ...partial };
      // Save serializable fields only
      const { sourceDoc, competitorDoc, characterFiles, ...serializable } = next;
      localStorage.setItem('wizard_data', JSON.stringify(serializable));
      return next;
    });

  const handleNext = () => {
    updateStep(step + 1);
  };

  const canNext = (): boolean => {
    if (step === 0) return !!data.sourceUrl || !!data.sourceDoc;
    if (step === 3) return !!data.openaiKey;
    if (step === 4) {
      // Must have at least one platform selected
      // Connection is optional — user can connect later from the Connect page
      return data.platforms.length > 0;
    }
    return true;
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      // Save API keys + OAuth creds to backend config
      const configPayload: Record<string, string> = {};
      if (data.openaiKey) configPayload.openai_api_key = data.openaiKey;
      if (data.pexelsKey) configPayload.pexels_api_key = data.pexelsKey;
      if (data.elevenlabsKey) configPayload.elevenlabs_api_key = data.elevenlabsKey;
      if (data.telegramToken) configPayload.telegram_bot_token = data.telegramToken;
      if (data.telegramChatId) configPayload.telegram_chat_id = data.telegramChatId;

      // OAuth creds no longer needed — using browser session login

      if (Object.keys(configPayload).length > 0) {
        await saveConfig(configPayload);
      }

      // Create the job
      const formData = new FormData();
      formData.append('source_url', data.sourceUrl || 'https://example.com');
      formData.append('language', data.language);
      formData.append('video_count', String(data.videoCount));
      formData.append('aspect_ratio', data.aspectRatio);
      formData.append('platforms', data.platforms.join(','));
      formData.append('niche', data.niche);
      formData.append('competitor_urls', data.competitorUrls.filter(Boolean).join(','));

      data.characterFiles.forEach((f) => {
        formData.append('character_files', f);
      });

      const result = await createJob(formData);
      // Reset step to 0 but KEEP wizard data for next time
      localStorage.setItem('wizard_step', '0');
      navigate(`/jobs/${result.job_id}`);
    } catch (err) {
      console.error('Submit failed:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const stepContent = [
    <SourceStep data={data} update={update} />,
    <CompetitorStep data={data} update={update} />,
    <AssetStep data={data} update={update} />,
    <ApiKeyStep data={data} update={update} />,
    <PlatformStep data={data} update={update} />,
    <TelegramStep data={data} update={update} />,
  ];

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 1, textAlign: 'center' }}>
        Create AI Video
      </Typography>
      <Typography
        variant="body1"
        sx={{ mb: 4, textAlign: 'center', color: 'text.secondary' }}
      >
        Automated pipeline: Content → Script → Video → Publish
      </Typography>

      <Stepper
        activeStep={step}
        alternativeLabel
        sx={{
          mb: 4,
          '& .MuiStepIcon-root.Mui-active': { color: theme.palette.primary.main },
          '& .MuiStepIcon-root.Mui-completed': { color: theme.palette.secondary.main },
        }}
      >
        {STEPS.map((label) => (
          <Step key={label}>
            <StepLabel
              sx={{
                '& .MuiStepLabel-label': {
                  fontSize: '0.8rem',
                  mt: 0.5,
                },
              }}
            >
              {label}
            </StepLabel>
          </Step>
        ))}
      </Stepper>

      <Fade in key={step} timeout={300}>
        <Paper
          sx={{
            p: 4,
            minHeight: 340,
            transition: 'box-shadow 0.3s ease',
            '&:hover': { boxShadow: '0 8px 24px rgba(15, 23, 42, 0.06)' },
          }}
        >
          {stepContent[step]}
        </Paper>
      </Fade>

      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button
          variant="outlined"
          onClick={() => updateStep(step - 1)}
          disabled={step === 0}
          startIcon={<ArrowBackIcon />}
          sx={{ borderColor: 'rgba(255,255,255,0.12)' }}
        >
          Back
        </Button>

        {step < STEPS.length - 1 ? (
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={!canNext()}
            endIcon={<ArrowForwardIcon />}
          >
            Next
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={submitting}
            endIcon={<RocketLaunchIcon />}
            sx={{
              background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
              px: 4,
              transition: 'all 0.25s ease',
              '&:hover': {
                background: 'linear-gradient(135deg, #4F46E5, #7C3AED)',
                transform: 'translateY(-1px)',
                boxShadow: '0 6px 20px rgba(99, 102, 241, 0.35)',
              },
            }}
          >
            {submitting ? 'Creating...' : 'Start pipeline'}
          </Button>
        )}
      </Box>
    </Box>
  );
}
