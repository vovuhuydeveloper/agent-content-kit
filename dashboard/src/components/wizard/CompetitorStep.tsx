import { Box, TextField, Typography, IconButton, Alert } from '@mui/material';
import AddCircleIcon from '@mui/icons-material/AddCircle';
import RemoveCircleIcon from '@mui/icons-material/RemoveCircle';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import type { WizardData } from '../../pages/SetupWizard';

interface Props {
  data: WizardData;
  update: (d: Partial<WizardData>) => void;
}

export default function CompetitorStep({ data, update }: Props) {
  const addUrl = () => update({ competitorUrls: [...data.competitorUrls, ''] });
  const removeUrl = (i: number) =>
    update({ competitorUrls: data.competitorUrls.filter((_, idx) => idx !== i) });
  const changeUrl = (i: number, val: string) => {
    const urls = [...data.competitorUrls];
    urls[i] = val;
    update({ competitorUrls: urls });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CompareArrowsIcon color="primary" /> Competitor Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Add competitor links so the AI can analyze their style, trends and create better content.
        <br />This step is optional — if left empty, AI will auto-analyze based on current trends.
      </Typography>

      {data.competitorUrls.map((url, i) => (
        <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <TextField
            label={`Competitor ${i + 1}`}
            placeholder="https://competitor-channel.com"
            value={url}
            onChange={(e) => changeUrl(i, e.target.value)}
            fullWidth
          />
          {data.competitorUrls.length > 1 && (
            <IconButton onClick={() => removeUrl(i)} color="error" size="small">
              <RemoveCircleIcon />
            </IconButton>
          )}
        </Box>
      ))}

      <Box>
        <IconButton onClick={addUrl} color="primary">
          <AddCircleIcon />
        </IconButton>
        <Typography variant="caption" color="text.secondary">
          Add competitor
        </Typography>
      </Box>

      <Alert severity="info" sx={{ borderRadius: 3 }}>
        💡 Tip: Add YouTube or TikTok channel links for AI to analyze their content style
      </Alert>
    </Box>
  );
}
