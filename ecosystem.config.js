module.exports = {
  apps : [{
    name: 'backpack_bot',
    script: `${process.env.HOME}/.backpack_bot/backpack_bot.py`,
    interpreter: 'python3',
    autorestart: true,
    watch: false,
    max_memory_restart: '200M',
    env: {
      NODE_ENV: 'production'
    },
    log_date_format: 'YYYY-MM-DD HH:mm:ss'
  }]
}; 