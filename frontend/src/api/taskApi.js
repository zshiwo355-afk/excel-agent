import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://127.0.0.1:8000/api",
  timeout: 60000,
});

export const getHealth = async () => {
  const { data } = await apiClient.get("/health");
  return data;
};

export const listTasks = async () => {
  const { data } = await apiClient.get("/tasks");
  return data;
};

export const getTask = async (taskId) => {
  const { data } = await apiClient.get(`/tasks/${taskId}`);
  return data;
};

export const createTask = async ({ message, file }) => {
  const formData = new FormData();
  formData.append("message", message);
  if (file) {
    formData.append("file", file);
  }
  const { data } = await apiClient.post("/tasks", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const confirmTask = async (taskId) => {
  const { data } = await apiClient.post(`/tasks/${taskId}/confirm`);
  return data;
};

export const getDownloadUrl = (taskId) =>
  `${apiClient.defaults.baseURL}/tasks/${taskId}/download`;
