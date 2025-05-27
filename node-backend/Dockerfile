FROM node:20-bullseye

# Set NODE_ENV to production
ENV NODE_ENV=production

WORKDIR /usr/src/app

# Copy package.json and package-lock.json first
COPY package*.json ./

# Install only production dependencies
RUN npm ci --omit=dev

# Copy source files
COPY . .

# Expose port 3000
EXPOSE 3000

# Run the node backend app in production mode
CMD ["node", "index.js"]  
