const ROWS = 6;
const COLS = 7;

const boardEl = document.querySelector('.board');
const statusEl = document.getElementById('status');
const resetBtn = document.getElementById('reset');

let board;
let currentPlayer;
let gameOver;
let messageTimeoutId;

function createBoardElements() {
  boardEl.innerHTML = '';
  const fragment = document.createDocumentFragment();
  boardEl.setAttribute('aria-rowcount', ROWS.toString());
  boardEl.setAttribute('aria-colcount', COLS.toString());

  for (let row = 0; row < ROWS; row += 1) {
    for (let col = 0; col < COLS; col += 1) {
      const cell = document.createElement('button');
      cell.className = 'cell';
      cell.type = 'button';
      cell.dataset.row = row;
      cell.dataset.column = col;
      cell.setAttribute('role', 'gridcell');
      cell.setAttribute('aria-label', `Rij ${row + 1}, kolom ${col + 1}, leeg`);

      const disc = document.createElement('span');
      disc.className = 'disc';
      cell.appendChild(disc);

      cell.addEventListener('click', () => handleColumnClick(col));
      cell.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          handleColumnClick(col);
        }
      });

      fragment.appendChild(cell);
    }
  }

  boardEl.appendChild(fragment);
}

function indexFromPosition(row, col) {
  return row * COLS + col;
}

function getCellElement(row, col) {
  return boardEl.children[indexFromPosition(row, col)];
}

function updateCell(row, col, player) {
  const cell = getCellElement(row, col);
  cell.classList.remove('winning');
  cell.classList.add('filled', `player${player}`);
  cell.setAttribute('aria-label', `Rij ${row + 1}, kolom ${col + 1}, steen speler ${player}`);
  cell.dataset.player = player;
}

function clearCell(row, col) {
  const cell = getCellElement(row, col);
  cell.className = 'cell';
  cell.removeAttribute('data-player');
  cell.setAttribute('aria-label', `Rij ${row + 1}, kolom ${col + 1}, leeg`);
}

function setStatus(message) {
  statusEl.textContent = message;
}

function scheduleStatusReset() {
  if (gameOver) {
    return;
  }
  clearTimeout(messageTimeoutId);
  messageTimeoutId = setTimeout(() => {
    if (!gameOver) {
      setStatus(`Speler ${currentPlayer} is aan zet`);
    }
  }, 1600);
}

function handleColumnClick(col) {
  if (gameOver) {
    return;
  }

  for (let row = ROWS - 1; row >= 0; row -= 1) {
    if (board[row][col] === 0) {
      placeDisc(row, col);
      return;
    }
  }

  setStatus('Deze kolom is vol. Kies een andere kolom.');
  scheduleStatusReset();
}

function placeDisc(row, col) {
  board[row][col] = currentPlayer;
  updateCell(row, col, currentPlayer);

  const winningCells = checkForWin(row, col, currentPlayer);
  if (winningCells) {
    gameOver = true;
    highlightWinningCells(winningCells);
    setStatus(`Speler ${currentPlayer} heeft gewonnen! 🎉`);
    return;
  }

  if (isDraw()) {
    gameOver = true;
    setStatus('Gelijkspel!');
    return;
  }

  currentPlayer = currentPlayer === 1 ? 2 : 1;
  setStatus(`Speler ${currentPlayer} is aan zet`);
}

function isDraw() {
  return board.every((row) => row.every((cell) => cell !== 0));
}

function highlightWinningCells(cells) {
  cells.forEach(([row, col]) => {
    const cell = getCellElement(row, col);
    cell.classList.add('winning');
  });
}

function checkForWin(row, col, player) {
  const directions = [
    [0, 1],
    [1, 0],
    [1, 1],
    [1, -1],
  ];

  for (const [dr, dc] of directions) {
    const forward = collectInDirection(row, col, dr, dc, player);
    const backward = collectInDirection(row, col, -dr, -dc, player).reverse();
    const line = [...backward, [row, col], ...forward];

    if (line.length >= 4) {
      for (let i = 0; i <= line.length - 4; i += 1) {
        return line.slice(i, i + 4);
      }
    }
  }

  return null;
}

function collectInDirection(row, col, dr, dc, player) {
  const cells = [];
  let r = row + dr;
  let c = col + dc;

  while (r >= 0 && r < ROWS && c >= 0 && c < COLS && board[r][c] === player) {
    cells.push([r, c]);
    r += dr;
    c += dc;
  }

  return cells;
}

function resetGame() {
  board = Array.from({ length: ROWS }, () => Array(COLS).fill(0));
  currentPlayer = 1;
  gameOver = false;
  clearTimeout(messageTimeoutId);
  setStatus('Speler 1 is aan zet');

  for (let row = 0; row < ROWS; row += 1) {
    for (let col = 0; col < COLS; col += 1) {
      clearCell(row, col);
    }
  }
}

resetBtn.addEventListener('click', resetGame);

createBoardElements();
resetGame();
