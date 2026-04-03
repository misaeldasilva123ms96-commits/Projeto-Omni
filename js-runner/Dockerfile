FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY src ./src
COPY js-runner ./js-runner
COPY contract ./contract

CMD ["node", "src/queryEngineRunnerAdapter.js"]
