import dotenv from 'dotenv';
import http from 'http';
import app from './app.js';       // <--- Note the .js extension
import connectDB from './config/db.js'; // <--- Note the .js extension

// Load env vars
dotenv.config();

// 1. Connect to Database
connectDB();

// 2. Create HTTP Server
const server = http.createServer(app);

// 3. Start Listening
const PORT = process.env.PORT || 4000;

server.listen(PORT, () => {
  console.log(`
  🚀 Service A (Operational) running on port ${PORT}
  --------------------------------------------------
  👉 Health Check: http://localhost:${PORT}/health
  👉 Environment:  ${process.env.NODE_ENV}
  `);
});

// 4. Handle Unhandled Rejections
process.on('unhandledRejection', (err) => {
  console.log('UNHANDLED REJECTION! 💥 Shutting down...');
  console.log(err.name, err.message);
  server.close(() => {
    process.exit(1);
  });
});