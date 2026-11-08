// ════════════════════════════════════════════════════════════════
//  AUDIO MANAGER — Web Audio API sound effects (no files needed)
// ════════════════════════════════════════════════════════════════

class AudioManager {
  constructor() {
    this._ctx = null;
    this._enabled = true;
    this._initialized = false;
  }

  _getContext() {
    if (!this._ctx) {
      try {
        this._ctx = new (window.AudioContext || window.webkitAudioContext)();
      } catch (e) {
        return null;
      }
    }
    if (this._ctx.state === 'suspended') {
      this._ctx.resume();
    }
    return this._ctx;
  }

  _play(fn) {
    if (!this._enabled) return;
    const ctx = this._getContext();
    if (!ctx) return;
    this._initialized = true;
    try { fn(ctx); } catch (e) { /* ignore audio errors */ }
  }

  _tone(ctx, freq, duration, type = 'sine', volume = 0.12, delay = 0) {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, ctx.currentTime + delay);
    gain.gain.setValueAtTime(volume, ctx.currentTime + delay);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(ctx.currentTime + delay);
    osc.stop(ctx.currentTime + delay + duration);
  }

  _noise(ctx, duration, volume = 0.04, delay = 0) {
    const bufferSize = ctx.sampleRate * duration;
    const buffer = ctx.createBuffer(1, bufferSize, ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(volume, ctx.currentTime + delay);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + delay + duration);
    source.connect(gain);
    gain.connect(ctx.destination);
    source.start(ctx.currentTime + delay);
  }

  click() {
    this._play(ctx => {
      this._tone(ctx, 800, 0.06, 'square', 0.04);
      this._tone(ctx, 1200, 0.04, 'sine', 0.03);
    });
  }

  countdown(step) {
    this._play(ctx => {
      const freqs = [400, 500, 650];
      const f = freqs[step] || 400;
      this._tone(ctx, f, 0.15, 'triangle', 0.08);
      this._tone(ctx, f * 1.5, 0.1, 'sine', 0.04);
    });
  }

  shoot() {
    this._play(ctx => {
      this._tone(ctx, 200, 0.25, 'sawtooth', 0.1);
      this._tone(ctx, 400, 0.15, 'square', 0.06);
      this._noise(ctx, 0.12, 0.06);
    });
  }

  roundWin() {
    this._play(ctx => {
      this._tone(ctx, 523, 0.15, 'sine', 0.08);
      this._tone(ctx, 659, 0.15, 'sine', 0.08, 0.12);
      this._tone(ctx, 784, 0.25, 'sine', 0.1, 0.24);
    });
  }

  roundLose() {
    this._play(ctx => {
      this._tone(ctx, 400, 0.2, 'triangle', 0.07);
      this._tone(ctx, 350, 0.2, 'triangle', 0.06, 0.15);
      this._tone(ctx, 300, 0.3, 'triangle', 0.05, 0.3);
    });
  }

  roundDraw() {
    this._play(ctx => {
      this._tone(ctx, 440, 0.12, 'sine', 0.06);
      this._tone(ctx, 440, 0.12, 'triangle', 0.04, 0.1);
    });
  }

  gameOverWin() {
    this._play(ctx => {
      const notes = [523, 659, 784, 1047];
      notes.forEach((f, i) => {
        this._tone(ctx, f, 0.2, 'sine', 0.08, i * 0.12);
      });
      this._tone(ctx, 1047, 0.5, 'sine', 0.12, 0.5);
    });
  }

  gameOverLose() {
    this._play(ctx => {
      this._tone(ctx, 350, 0.3, 'triangle', 0.07);
      this._tone(ctx, 260, 0.3, 'triangle', 0.06, 0.25);
      this._tone(ctx, 200, 0.5, 'triangle', 0.05, 0.5);
    });
  }

  nextRound() {
    this._play(ctx => {
      this._tone(ctx, 600, 0.08, 'sine', 0.05);
      this._tone(ctx, 800, 0.08, 'sine', 0.04, 0.06);
      this._tone(ctx, 1000, 0.1, 'sine', 0.03, 0.12);
    });
  }

  swarmActivate(name) {
    this._play(ctx => {
      const tones = {
        'GameMaster': [800, 1000, 1200],
        'BotStrategist': [500, 650, 800],
        'ScoreAnalyst': [600, 750, 900],
        'Narrator': [700, 850, 1000],
      };
      const freqs = tones[name] || [600, 800, 1000];
      freqs.forEach((f, i) => {
        this._tone(ctx, f, 0.06, 'sine', 0.04, i * 0.05);
      });
    });
  }

  confetti() {
    this._play(ctx => {
      for (let i = 0; i < 12; i++) {
        const f = 800 + Math.random() * 2000;
        const t = 0.1 + Math.random() * 0.4;
        this._tone(ctx, f, 0.08, 'sine', 0.02 + Math.random() * 0.03, t);
      }
    });
  }

  toggle() {
    this._enabled = !this._enabled;
    if (this._enabled && !this._initialized) {
      this._play(() => {});
    }
    return this._enabled;
  }
}

const audio = new AudioManager();

function toggleSound() {
  const enabled = audio.toggle();
  document.querySelectorAll('.btn-sound, .card-btn-sound').forEach(btn => {
    btn.textContent = enabled ? '🔊' : '🔇';
    btn.classList.toggle('muted', !enabled);
  });
}

// ════════════════════════════════════════════════════════════════
//  SWARM AGENT SYSTEM (JavaScript)
// ════════════════════════════════════════════════════════════════

class Agent {
  constructor(name, instructions, fn = null) {
    this.name = name;
    this.instructions = instructions;
    this.fn = fn;
  }
  execute(...args) {
    if (this.fn) return this.fn(...args);
    return null;
  }
}

class EventBus {
  constructor() {
    this._subscribers = {};
  }
  subscribe(hook, callback) {
    if (!this._subscribers[hook]) this._subscribers[hook] = [];
    this._subscribers[hook].push(callback);
  }
  emit(hook, data = {}) {
    (this._subscribers[hook] || []).forEach(cb => {
      try { cb(data); } catch (e) { /* ignore */ }
    });
  }
}

const CHOICES = ['rock', 'paper', 'scissors'];
const CHOICE_EMOJI = { rock: '✊', paper: '✋', scissors: '✌️' };
const CHOICE_NAME = { rock: 'Rock', paper: 'Paper', scissors: 'Scissors' };
const CHOICE_BEATS = { rock: 'scissors', paper: 'rock', scissors: 'paper' };

const BotStrategist = new Agent('BotStrategist',
  'Analyze player patterns and make strategic counter-moves',
  (playerHistory) => {
    const history = playerHistory || [];
    if (history.length === 0) {
      return { choice: CHOICES[Math.floor(Math.random() * 3)], strategy: 'random' };
    }
    if (history.length === 1) {
      const counter = Object.keys(CHOICE_BEATS).find(k => CHOICE_BEATS[k] === history[0]);
      return { choice: counter || CHOICES[0], strategy: 'counter' };
    }
    const last = history[history.length - 1];
    const secondLast = history[history.length - 2];
    if (last === secondLast && history.length >= 2) {
      const counter = Object.keys(CHOICE_BEATS).find(k => CHOICE_BEATS[k] === last);
      return { choice: counter || CHOICES[0], strategy: 'pattern' };
    }
    if (history.length >= 3) {
      const p3 = history[history.length - 3];
      if (p3 === last && secondLast !== last) {
        const counter = Object.keys(CHOICE_BEATS).find(k => CHOICE_BEATS[k] === secondLast);
        return { choice: counter || CHOICES[0], strategy: 'pattern' };
      }
      const last3 = history.slice(-3);
      if (last3[0] === 'rock' && last3[1] === 'paper' && last3[2] === 'scissors') {
        return { choice: 'rock', strategy: 'pattern' };
      }
    }
    const counter = Object.keys(CHOICE_BEATS).find(k => CHOICE_BEATS[k] === last);
    return { choice: counter || CHOICES[0], strategy: 'adaptive' };
  }
);

const ScoreAnalyst = new Agent('ScoreAnalyst',
  'Track game statistics and generate performance insights',
  (gameState) => {
    const { playerScore, botScore, wins, losses, draws, rounds, bestOf } = gameState;
    const total = rounds.length;
    const stats = {
      totalRounds: total,
      winRate: total > 0 ? Math.round((wins / total) * 100) : 0,
      lossRate: total > 0 ? Math.round((losses / total) * 100) : 0,
      drawRate: total > 0 ? Math.round((draws / total) * 100) : 0,
      scoreDiff: playerScore - botScore,
      prediction: ''
    };
    if (playerScore > botScore) {
      stats.prediction = `You're ahead ${playerScore}-${botScore}. ` +
        (playerScore >= Math.ceil(bestOf / 2) ? 'Match point!' : 'Keep the pressure on!');
    } else if (botScore > playerScore) {
      stats.prediction = `Trailing ${playerScore}-${botScore}. ` +
        (botScore >= Math.ceil(bestOf / 2) ? 'The bot has match point!' : 'Time for a comeback!');
    } else {
      stats.prediction = `All tied at ${playerScore}. Every round counts!`;
    }
    return stats;
  }
);

const Narrator = new Agent('Narrator',
  'Provide engaging thematic commentary for the game',
  (winner, playerChoice, botChoice, strategy) => {
    const comments = {
      player: [
        `A brilliant move! ${CHOICE_EMOJI[playerChoice]} beats ${CHOICE_EMOJI[botChoice]}!`,
        `Outplayed! The bot's ${strategy} strategy was no match for you!`,
        `Flawless victory! ${CHOICE_NAME[playerChoice]} triumphs over ${CHOICE_NAME[botChoice]}!`,
        `The crowd erupts as your ${CHOICE_NAME[playerChoice]} crushes the bot's ${CHOICE_NAME[botChoice]}!`,
        `Textbook play! You read the situation perfectly!`,
        `The bot reels from that decisive ${CHOICE_NAME[playerChoice]}!`,
      ],
      bot: [
        `The bot counters with ${CHOICE_NAME[botChoice]}! A calculated move.`,
        `The algorithm saw that coming! ${CHOICE_NAME[botChoice]} prevails.`,
        `A cold, logical choice from the machine mind. ${CHOICE_NAME[botChoice]} wins this round.`,
        `The bot's ${strategy} analysis paid off! ${CHOICE_NAME[botChoice]} takes the round.`,
        `Even the best get outplayed. The bot claims this round with ${CHOICE_NAME[botChoice]}.`,
      ],
      draw: [
        `Great minds think alike! Both chose ${CHOICE_NAME[playerChoice]}!`,
        `A perfect mirror! Neither gains an edge.`,
        `Symmetry in the arena! Both players matched.`,
        `The universe seeks balance... a ${CHOICE_NAME[playerChoice]} standoff!`,
        `Neither blinks first! A ${CHOICE_NAME[playerChoice]} stalemate!`,
      ]
    };
    const pool = comments[winner] || comments.draw;
    return pool[Math.floor(Math.random() * pool.length)];
  }
);

const GameMaster = new Agent('GameMaster',
  'Orchestrate game flow, validate moves, manage state transitions',
  null
);

class RpsOrchestrator {
  constructor() {
    this.eventBus = new EventBus();
    this.botStrategist = BotStrategist;
    this.scoreAnalyst = ScoreAnalyst;
    this.narrator = Narrator;
    this.gameMaster = GameMaster;
  }

  setAgentActive(agentName) {
    this.eventBus.emit('agent_activated', { agent: agentName });
    const dotMap = { 'GameMaster': 'dot-gm', 'BotStrategist': 'dot-bs', 'ScoreAnalyst': 'dot-sa', 'Narrator': 'dot-nr' };
    document.querySelectorAll('.swarm-agent-dot').forEach(d => d.classList.remove('active', 'done'));
    const dotId = dotMap[agentName];
    if (dotId) { const dot = document.getElementById(dotId); if (dot) dot.classList.add('active'); }
  }

  setAgentDone(agentName) {
    const dotMap = { 'GameMaster': 'dot-gm', 'BotStrategist': 'dot-bs', 'ScoreAnalyst': 'dot-sa', 'Narrator': 'dot-nr' };
    const dotId = dotMap[agentName];
    if (dotId) { const dot = document.getElementById(dotId); if (dot) { dot.classList.remove('active'); dot.classList.add('done'); } }
  }

  /**
   * Builds the status line from DOM nodes instead of injecting HTML, so the
   * interpolated round/comment text can never be parsed as markup.
   */
  setSwarmText(prefix, highlight, suffix) {
    const el = document.getElementById('swarmText');
    if (el) {
      el.textContent = '';
      if (prefix) el.appendChild(document.createTextNode(prefix));
      if (highlight) {
        const span = document.createElement('span');
        span.className = 'highlight';
        span.textContent = highlight;
        el.appendChild(span);
      }
      if (suffix) el.appendChild(document.createTextNode(suffix));
      el.classList.remove('animate');
      void el.offsetWidth;
      el.classList.add('animate');
    }
  }

  async resolveRound(playerChoice, gameState) {
    this.setAgentActive('BotStrategist');
    this.setSwarmText('🧠 ', 'BotStrategist', ' analyzing your patterns...');
    await sleep(400);

    const { choice: botChoice, strategy } = this.botStrategist.execute(gameState.playerHistory);
    this.setAgentDone('BotStrategist');

    let winner;
    if (playerChoice === botChoice) winner = 'draw';
    else if (CHOICE_BEATS[playerChoice] === botChoice) winner = 'player';
    else winner = 'bot';

    this.setAgentActive('GameMaster');
    this.setSwarmText('🎮 ', 'GameMaster', ` resolving round ${gameState.currentRound + 1}...`);
    await sleep(300);
    this.setAgentDone('GameMaster');

    this.setAgentActive('ScoreAnalyst');
    const newState = { ...gameState };
    newState.playerScore += (winner === 'player' ? 1 : 0);
    newState.botScore += (winner === 'bot' ? 1 : 0);
    newState.wins += (winner === 'player' ? 1 : 0);
    newState.losses += (winner === 'bot' ? 1 : 0);
    newState.draws += (winner === 'draw' ? 1 : 0);
    newState.rounds = [...(gameState.rounds || []), { playerChoice, botChoice, winner }];
    newState.playerHistory = [...(gameState.playerHistory || []), playerChoice];

    const stats = this.scoreAnalyst.execute(newState);
    this.setSwarmText('📊 ', 'ScoreAnalyst', `: ${stats.prediction}`);
    await sleep(300);
    this.setAgentDone('ScoreAnalyst');

    this.setAgentActive('Narrator');
    const strategyNames = { random: '🎲 Random', counter: '🔄 Counter', pattern: '📊 Pattern Analysis', adaptive: '🧠 Adaptive' };
    const comment = this.narrator.execute(winner, playerChoice, botChoice, strategyNames[strategy] || strategy);
    this.setSwarmText('📖 ', 'Narrator', `: ${comment}`);
    await sleep(400);
    this.setAgentDone('Narrator');

    return { botChoice, strategy, strategyName: strategyNames[strategy] || strategy, winner, stats, newState, comment };
  }
}

// ════════════════════════════════════════════════════════════════
//  GAME STATE
// ════════════════════════════════════════════════════════════════

const state = {
  bestOf: 5,
  rounds: [],
  currentRound: 0,
  playerScore: 0,
  botScore: 0,
  wins: 0,
  losses: 0,
  draws: 0,
  maxRounds: 0,
  playerChoice: null,
  botChoice: null,
  isPlaying: false,
  isLocked: false,
  playerHistory: [],
  roundStrategies: [],
};

const orchestrator = new RpsOrchestrator();

const $ = id => document.getElementById(id);
const el = {
  homeScreen: $('homeScreen'),
  appContainer: $('appContainer'),
  modeScreen: $('modeScreen'),
  gameScreen: $('gameScreen'),
  resultsScreen: $('resultsScreen'),
  roundLabel: $('roundLabel'),
  roundDots: $('roundDots'),
  playerScore: $('playerScore'),
  botScore: $('botScore'),
  statusText: $('statusText'),
  playerChoiceDisplay: $('playerChoiceDisplay'),
  playerChoiceEmoji: $('playerChoiceEmoji'),
  botChoiceDisplay: $('botChoiceDisplay'),
  botChoiceEmoji: $('botChoiceEmoji'),
  vsBadge: $('vsBadge'),
  battleArea: $('battleArea'),
  countdownOverlay: $('countdownOverlay'),
  strategyText: $('strategyText'),
  nextBtn: $('nextBtn'),
  swarmText: $('swarmText'),
  resultsIcon: $('resultsIcon'),
  resultsTitle: $('resultsTitle'),
  resultsSub: $('resultsSub'),
  rWins: $('rWins'),
  rLosses: $('rLosses'),
  rDraws: $('rDraws'),
  resultsSummaryText: $('resultsSummaryText'),
  confettiContainer: $('confettiContainer'),
  bestofOptions: $('bestofOptions'),
  bgEffects: $('bgEffects'),
  bgStars: $('bgStars'),
};

// ── Stars Background ───────────────────────────────────────────
(function createStars() {
  const container = $('bgStars');
  for (let i = 0; i < 50; i++) {
    const star = document.createElement('div');
    star.className = 'star';
    star.style.left = Math.random() * 100 + '%';
    star.style.top = Math.random() * 100 + '%';
    star.style.animationDelay = Math.random() * 3 + 's';
    star.style.width = star.style.height = (1 + Math.random() * 2) + 'px';
    container.appendChild(star);
  }
})();

// ════════════════════════════════════════════════════════════════
//  HELPERS
// ════════════════════════════════════════════════════════════════

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function switchScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  $(id).classList.add('active');
}

function getWinner(p, b) {
  if (p === b) return 'draw';
  if ((p === 'rock' && b === 'scissors') ||
      (p === 'paper' && b === 'rock') ||
      (p === 'scissors' && b === 'paper')) return 'player';
  return 'bot';
}

// ════════════════════════════════════════════════════════════════
//  FLOW: Home → Mode Select → Game → Results
// ════════════════════════════════════════════════════════════════

function showModeScreen() {
  // Hide home, show app with background effects (click sound handled by ripple)
  el.homeScreen.classList.add('hidden');
  el.bgEffects.classList.add('visible');
  el.bgStars.classList.add('visible');
  el.appContainer.classList.remove('hidden');
  // Delay mode screen switch slightly to let bg fade in
  setTimeout(() => switchScreen('modeScreen'), 200);
}

// Mode: Best Of Selector
el.bestofOptions.addEventListener('click', (e) => {
  const btn = e.target.closest('.bestof-opt');
  if (!btn) return;
  audio.click();
  document.querySelectorAll('.bestof-opt').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  state.bestOf = parseInt(btn.dataset.value);
});

// Mode: Enter Arena
function enterArena() {
  // Click sound handled by ripple handler
  startGame();
}

// ════════════════════════════════════════════════════════════════
//  GAME START
// ════════════════════════════════════════════════════════════════

function startGame() {
  state.maxRounds = state.bestOf;
  state.currentRound = 0;
  state.rounds = [];
  state.playerScore = 0;
  state.botScore = 0;
  state.wins = 0;
  state.losses = 0;
  state.draws = 0;
  state.isLocked = false;
  state.playerHistory = [];
  state.roundStrategies = [];
  state.isPlaying = true;

  switchScreen('gameScreen');
  buildRoundDots();
  updateScore();
  updateRoundLabel();
  resetBattleArea();
  enableChoices(true);
  setStatus('Choose your move');
  el.nextBtn.classList.remove('show');
  el.strategyText.classList.remove('show');

  document.querySelectorAll('.swarm-agent-dot').forEach(d => d.classList.remove('active', 'done'));
  orchestrator.setSwarmText('🎮 ', 'GameMaster', ' is ready. Waiting for your move...');

  audio.click();

  animateSwarmAgents();
}

async function animateSwarmAgents() {
  const agents = [
    { id: 'dot-gm', name: 'GameMaster' },
    { id: 'dot-bs', name: 'BotStrategist' },
    { id: 'dot-sa', name: 'ScoreAnalyst' },
    { id: 'dot-nr', name: 'Narrator' },
  ];

  for (const a of agents) {
    const dot = $(a.id);
    if (dot) {
      dot.classList.add('active');
      audio.swarmActivate(a.name);
      await sleep(250);
      dot.classList.remove('active');
      dot.classList.add('done');
    }
  }
  audio.click();
  audio.click();
  await sleep(100);
  document.querySelectorAll('.swarm-agent-dot').forEach(d => d.classList.remove('active', 'done'));
}

function buildRoundDots() {
  el.roundDots.innerHTML = '';
  for (let i = 0; i < state.maxRounds; i++) {
    const dot = document.createElement('div');
    dot.className = 'round-dot' + (i === 0 ? ' current' : '');
    dot.dataset.index = i;
    el.roundDots.appendChild(dot);
  }
}

function updateRoundLabel() {
  el.roundLabel.textContent = `Round ${state.currentRound + 1} of ${state.maxRounds}`;
}

function updateScore() {
  el.playerScore.textContent = state.playerScore;
  el.botScore.textContent = state.botScore;
}

function updateRoundDot(index, result) {
  const dots = el.roundDots.querySelectorAll('.round-dot');
  dots.forEach(d => d.classList.remove('current'));
  if (index < dots.length) {
    dots[index].classList.add(result);
    if (index + 1 < dots.length) dots[index + 1].classList.add('current');
  }
}

function resetBattleArea() {
  el.playerChoiceEmoji.textContent = '❔';
  el.botChoiceEmoji.textContent = '🗿';
  el.playerChoiceDisplay.className = 'choice-display';
  el.botChoiceDisplay.className = 'choice-display';
  el.battleArea.classList.remove('revealing');
  el.countdownOverlay.classList.remove('show', 'shoot');
  el.strategyText.classList.remove('show');
  el.strategyText.textContent = '';
}

function enableChoices(enabled) {
  document.querySelectorAll('.btn-choice').forEach(b => b.disabled = !enabled);
  state.isLocked = !enabled;
}

function setStatus(text, cls = '') {
  el.statusText.textContent = text;
  el.statusText.className = 'status-text' + (cls ? ' ' + cls : '');
}

// ════════════════════════════════════════════════════════════════
//  PLAYER CHOICE + SWARM PIPELINE
// ════════════════════════════════════════════════════════════════

async function playerChoice(choice) {
  if (state.isLocked || !state.isPlaying) return;
  state.playerChoice = choice;
  enableChoices(false);
  el.nextBtn.classList.remove('show');

  el.playerChoiceEmoji.textContent = CHOICE_EMOJI[choice];
  el.battleArea.classList.add('revealing');
  setStatus('');

  const overlay = el.countdownOverlay;
  const phrases = ['Rock…', 'Paper…', 'Scissors…', 'SHOOT!'];
  const timings = [500, 1000, 1500, 2000];
  const revealTime = 2100;

  el.botChoiceDisplay.classList.add('shaking');
  el.playerChoiceDisplay.classList.add('shaking');

  audio.click();

  phrases.forEach((phrase, i) => {
    setTimeout(() => {
      overlay.textContent = phrase;
      overlay.className = 'countdown-overlay show';
      if (i === 3) {
        overlay.classList.add('shoot');
        audio.shoot();
      } else {
        audio.countdown(i);
      }
    }, timings[i]);
  });

  const swarmResult = orchestrator.resolveRound(choice, { ...state });

  setTimeout(async () => {
    overlay.classList.remove('show', 'shoot');
    el.botChoiceDisplay.classList.remove('shaking');
    el.playerChoiceDisplay.classList.remove('shaking');

    const result = await swarmResult;
    revealResult(result);
  }, revealTime);
}

// ════════════════════════════════════════════════════════════════
//  REVEAL RESULT
// ════════════════════════════════════════════════════════════════

function revealResult(result) {
  const { botChoice, strategy, strategyName, winner, stats, newState, comment } = result;

  el.botChoiceEmoji.textContent = CHOICE_EMOJI[botChoice];
  el.battleArea.classList.remove('revealing');

  audio.swarmActivate('Narrator');

  state.currentRound++;
  state.botChoice = botChoice;

  const pBox = el.playerChoiceDisplay;
  const bBox = el.botChoiceDisplay;

  const resultClasses = { player: 'win', bot: 'lose', draw: 'draw' };
  const statusTexts = {
    player: `${CHOICE_NAME[state.playerChoice]} beats ${CHOICE_NAME[botChoice]} — You win!`,
    bot: `${CHOICE_NAME[botChoice]} beats ${CHOICE_NAME[state.playerChoice]} — Bot wins!`,
    draw: `Both chose ${CHOICE_NAME[state.playerChoice]} — Draw!`,
  };
  const statusClasses = { player: 'win-text', bot: 'lose-text', draw: 'draw-text' };

  pBox.className = `choice-display ${resultClasses[winner]}`;
  bBox.className = `choice-display ${winner === 'draw' ? 'draw' : (winner === 'player' ? 'lose' : 'win')}`;
  setStatus(statusTexts[winner], statusClasses[winner]);

  if (winner === 'player') audio.roundWin();
  else if (winner === 'bot') audio.roundLose();
  else audio.roundDraw();

  el.strategyText.textContent = `🤖 Bot used: ${strategyName}`;
  el.strategyText.classList.add('show');

  Object.assign(state, {
    playerScore: newState.playerScore,
    botScore: newState.botScore,
    wins: newState.wins,
    losses: newState.losses,
    draws: newState.draws,
    playerHistory: newState.playerHistory,
  });
  state.rounds.push({ playerChoice: state.playerChoice, botChoice, winner });
  state.roundStrategies.push(strategy);

  updateScore();
  updateRoundDot(state.currentRound - 1, resultClasses[winner]);

  const half = Math.ceil(state.maxRounds / 2);
  const gameOver = state.playerScore >= half || state.botScore >= half || state.currentRound >= state.maxRounds;

  if (gameOver) {
    state.isPlaying = false;
    setTimeout(showResults, 1200);
  } else {
    setTimeout(() => {
      el.nextBtn.classList.add('show');
      audio.nextRound();
      el.nextBtn.focus();
    }, 800);
  }
}

// ════════════════════════════════════════════════════════════════
//  NEXT ROUND
// ════════════════════════════════════════════════════════════════

function nextRound() {
  el.nextBtn.classList.remove('show');
  resetBattleArea();
  updateRoundLabel();
  enableChoices(true);
  setStatus('Choose your move');
  orchestrator.setSwarmText('🎮 ', 'GameMaster', ` ready. Round ${state.currentRound + 1} awaits...`);
  document.querySelectorAll('.btn-choice')[0].focus();
}

// ════════════════════════════════════════════════════════════════
//  SHOW RESULTS
// ════════════════════════════════════════════════════════════════

function showResults() {
  switchScreen('resultsScreen');

  const won = state.playerScore > state.botScore;
  const isDraw = state.playerScore === state.botScore;

  if (won) {
    el.resultsIcon.textContent = '🏆';
    el.resultsTitle.textContent = 'Victory!';
    el.resultsTitle.className = 'results-title win';
    el.resultsSub.textContent = `Final score: ${state.playerScore} - ${state.botScore}`;
    audio.gameOverWin();
    spawnConfetti();
  } else if (isDraw) {
    el.resultsIcon.textContent = '🤝';
    el.resultsTitle.textContent = "It's a Tie!";
    el.resultsTitle.className = 'results-title draw-title';
    el.resultsSub.textContent = `Final score: ${state.playerScore} - ${state.botScore}`;
    audio.roundDraw();
  } else {
    el.resultsIcon.textContent = '😔';
    el.resultsTitle.textContent = 'Defeat';
    el.resultsTitle.className = 'results-title lose';
    el.resultsSub.textContent = `Final score: ${state.playerScore} - ${state.botScore}`;
    audio.gameOverLose();
  }

  el.rWins.textContent = state.wins;
  el.rLosses.textContent = state.losses;
  el.rDraws.textContent = state.draws;

  const total = state.rounds.length;
  const winRate = total > 0 ? Math.round((state.wins / total) * 100) : 0;
  const summary = [
    `📊 Match Summary (Best of ${state.maxRounds})`,
    ``,
    `   Score:   You ${state.playerScore}  —  ${state.botScore} Bot`,
    `   Rounds:  ${total} played`,
    `   Win Rate:  ${winRate}%  (${state.wins}W / ${state.losses}L / ${state.draws}D)`,
    ``,
    `🤖 Bot Strategies Used:`,
    ...countStrategies().map(s => `   • ${s.emoji} ${s.name}: ${s.count}x`),
    ``,
    `🧠 Swarm Agents Activated:`,
    `   ✓ BotStrategist — Pattern analysis & counter-move selection`,
    `   ✓ GameMaster — Round validation & state management`,
    `   ✓ ScoreAnalyst — Real-time statistics & predictions`,
    `   ✓ Narrator — Thematic commentary & flavor text`,
  ].join('\n');

  el.resultsSummaryText.textContent = summary;
}

function countStrategies() {
  const strategyNames = {
    random: { name: 'Random Guess', emoji: '🎲' },
    counter: { name: 'Counter Move', emoji: '🔄' },
    pattern: { name: 'Pattern Recognition', emoji: '📊' },
    adaptive: { name: 'Adaptive Strategy', emoji: '🧠' },
  };
  const counts = {};
  (state.roundStrategies || []).forEach(s => { counts[s] = (counts[s] || 0) + 1; });
  if (Object.keys(counts).length === 0) {
    return [{ name: 'Tracking...', emoji: '🔄', count: state.rounds.length }];
  }
  return Object.entries(counts).map(([key, count]) => ({
    ...(strategyNames[key] || { name: key, emoji: '🤖' }),
    count,
  })).sort((a, b) => b.count - a.count);
}

// ════════════════════════════════════════════════════════════════
//  CONFETTI
// ════════════════════════════════════════════════════════════════

function spawnConfetti() {
  const container = el.confettiContainer;
  container.innerHTML = '';
  const colors = ['#6c3bff', '#00c48c', '#ff6b6b', '#ffb800', '#4a9eff', '#ff9ff3', '#9d7aff'];
  for (let i = 0; i < 60; i++) {
    const piece = document.createElement('div');
    piece.className = 'confetti-piece';
    const color = colors[Math.floor(Math.random() * colors.length)];
    const size = 5 + Math.random() * 8;
    const left = Math.random() * 100;
    const duration = 2 + Math.random() * 2;
    const delay = Math.random() * 1.5;
    piece.style.width = size + 'px';
    piece.style.height = size * (0.5 + Math.random()) + 'px';
    piece.style.background = color;
    piece.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
    piece.style.left = left + '%';
    piece.style.animationDuration = duration + 's';
    piece.style.animationDelay = delay + 's';
    container.appendChild(piece);
  }
  audio.confetti();
  setTimeout(() => audio.confetti(), 400);
  setTimeout(() => container.innerHTML = '', 6000);
}

// ════════════════════════════════════════════════════════════════
//  REMATCH / GO HOME
// ════════════════════════════════════════════════════════════════

function rematch() {
  el.confettiContainer.innerHTML = '';
  switchScreen('gameScreen');
  startGame();
}

function goHome() {
  el.confettiContainer.innerHTML = '';
  state.isPlaying = false;
  // Hide background effects and app, show home
  el.bgEffects.classList.remove('visible');
  el.bgStars.classList.remove('visible');
  el.appContainer.classList.add('hidden');
  el.homeScreen.classList.remove('hidden');
}

// ════════════════════════════════════════════════════════════════
//  KEYBOARD SHORTCUTS
// ════════════════════════════════════════════════════════════════

document.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

  const gameActive = el.gameScreen.classList.contains('active');
  const resultsActive = el.resultsScreen.classList.contains('active');
  const homeActive = !el.homeScreen.classList.contains('hidden');
  const modeActive = el.modeScreen.classList.contains('active');

  if (gameActive && !state.isLocked && state.isPlaying) {
    if (e.key === '1') { e.preventDefault(); playerChoice('rock'); }
    else if (e.key === '2') { e.preventDefault(); playerChoice('paper'); }
    else if (e.key === '3') { e.preventDefault(); playerChoice('scissors'); }
  }

  if (gameActive && el.nextBtn.classList.contains('show')) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      nextRound();
    }
  }

  if (resultsActive) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      rematch();
    }
    if (e.key === 'Escape') {
      e.preventDefault();
      goHome();
    }
  }

  if (homeActive && e.key === 'Enter') {
    e.preventDefault();
    // Check if home screen is still visible
    if (!el.homeScreen.classList.contains('hidden')) {
      showModeScreen();
    }
  }

  if (modeActive && e.key === 'Enter') {
    e.preventDefault();
    enterArena();
  }
});

// ════════════════════════════════════════════════════════════════
//  BUTTON RIPPLE EFFECT
// ════════════════════════════════════════════════════════════════
document.querySelectorAll('.btn-home-play, .btn-battle, .btn-rematch, .btn-home, .btn-next').forEach(btn => {
  btn.addEventListener('click', function(e) {
    audio.click();
    const rect = this.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    this.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
  });
});

// Choice buttons: ripple only (click sound handled by playerChoice)
document.querySelectorAll('.btn-choice').forEach(btn => {
  btn.addEventListener('click', function(e) {
    const rect = this.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    this.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
  });
});

// ════════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════════

console.log('🌀 Rock Paper Scissors — Swarm Arena loaded!');
console.log('  Agents: GameMaster, BotStrategist, ScoreAnalyst, Narrator');
console.log('  Press Enter to play | 1 (Rock) | 2 (Paper) | 3 (Scissors)');$

// ════════════════════════════════════════════════════════════════
//  EVENT WIRING — replaces the former inline on* attributes
// ════════════════════════════════════════════════════════════════

function on(node, type, handler) {
  if (node) node.addEventListener(type, handler);
}

on($('playBtn'), 'click', () => showModeScreen());
on($('battleBtn'), 'click', () => enterArena());
on($('nextBtn'), 'click', () => nextRound());

document.querySelectorAll('.btn-choice').forEach((btn) => {
  on(btn, 'click', () => playerChoice(btn.dataset.choice));
});

document.querySelectorAll('.btn-home').forEach((btn) => {
  on(btn, 'click', () => goHome());
});

document.querySelectorAll('.btn-rematch').forEach((btn) => {
  on(btn, 'click', () => rematch());
});

document
  .querySelectorAll('#soundToggle, #cardSoundToggle, #gameSoundToggle, #resultsSoundToggle')
  .forEach((btn) => {
    on(btn, 'click', () => toggleSound());
  });
