FROM node:20-alpine

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend ./

ARG VITE_OMNI_API_URL=http://localhost:3001
ENV VITE_OMNI_API_URL=${VITE_OMNI_API_URL}

ARG VITE_SUPABASE_URL=https://example.supabase.co
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}

ARG VITE_SUPABASE_ANON_KEY=example-anon-key
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}

RUN npm run build

EXPOSE 4173

CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
