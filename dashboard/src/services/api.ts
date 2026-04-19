import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

/* ── Jobs ── */
export const createJob = async (data: FormData) => {
  const res = await api.post('/content-jobs/', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
};

export const getJobs = async (limit = 20) => {
  const res = await api.get(`/content-jobs/?limit=${limit}`);
  return res.data;
};

export const getJob = async (id: string) => {
  const res = await api.get(`/content-jobs/${id}`);
  return res.data;
};

export const approveJob = async (id: string) => {
  const res = await api.post(`/content-jobs/${id}/approve`);
  return res.data;
};

export const rejectJob = async (id: string) => {
  const res = await api.post(`/content-jobs/${id}/reject`);
  return res.data;
};

export const deleteJob = async (id: string) => {
  const res = await api.delete(`/content-jobs/${id}`);
  return res.data;
};

export const getJobFiles = async (id: string) => {
  const res = await api.get(`/content-jobs/${id}/files`);
  return res.data;
};

/* ── Config ── */
export const saveConfig = async (config: Record<string, string>) => {
  const res = await api.post('/config/keys', config);
  return res.data;
};

export const getConfig = async () => {
  const res = await api.get('/config/keys');
  return res.data;
};

export const validateKey = async (service: string, key: string) => {
  const res = await api.post('/config/keys/validate', { service, key });
  return res.data;
};

export const testTelegramBot = async (token: string, chatId: string) => {
  const res = await api.post('/config/telegram/test', { token, chat_id: chatId });
  return res.data;
};

export const detectTelegramChat = async (token: string) => {
  const res = await api.post('/config/telegram/detect-chat', { token });
  return res.data;
};

export default api;
