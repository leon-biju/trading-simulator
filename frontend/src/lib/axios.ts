import axios from 'axios'

const api = axios.create({
  baseURL: '',
  withCredentials: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
})

export default api
