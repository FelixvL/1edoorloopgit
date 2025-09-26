const ROWS = 6;
const COLS = 7;
const boardElement = document.getElementById("board");
const cellTemplate = document.getElementById("cell-template");
const turnIndicator = document.getElementById("turn-indicator");
const resetButton = document.getElementById("reset-button");

let boardState;
let currentPlayer;
let gameOver;

function createEmptyBoard() {
  return Array.from({ length: ROWS }, () => Array(COLS).fill(0));
}

function setupBoard() {
  boardElement.innerHTML = "";
  const fragment = document.createDocumentFragment();

  for (let row = 0; row < ROWS; row += 1) {
    for (let col = 0; col < COLS; col += 1) {
      const cell = cellTemplate.content.firstElementChild.cloneNode(true);
      cell.dataset.row = row;
      cell.dataset.column = col;
      cell.addEventListener("click", () => handleMove(col));
      cell.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleMove(col);
        }
      });
      fragment.append(cell);
    }
  }

  boardElement.append(fragment);
}

function updateTurnIndicator(message) {
  if (message) {
    turnIndicator.textContent = message;
    return;
  }

  const playerName = currentPlayer === 1 ? "Rood" : "Geel";
  turnIndicator.textContent = `Beurt: speler ${playerName}`;
}

function handleMove(column) {
  if (gameOver) return;

  const columnCells = [];
  for (let row = ROWS - 1; row >= 0; row -= 1) {
    if (boardState[row][column] === 0) {
      columnCells.push(row);
    }
  }

  const targetRow = columnCells[0];

  if (targetRow === undefined) {
    updateTurnIndicator("Deze kolom is vol, kies een andere.");
    setTimeout(() => updateTurnIndicator(), 1500);
    return;
  }

  boardState[targetRow][column] = currentPlayer;
  paintBoard();

  const winningCells = checkWin(targetRow, column);
  if (winningCells) {
    highlightWinningCells(winningCells);
    updateTurnIndicator(`Speler ${currentPlayer === 1 ? "Rood" : "Geel"} wint!`);
    gameOver = true;
    return;
  }

  if (isBoardFull()) {
    updateTurnIndicator("Gelijkspel! Het bord is vol.");
    gameOver = true;
    return;
  }

  currentPlayer = currentPlayer === 1 ? 2 : 1;
  updateTurnIndicator();
}

function paintBoard() {
  const cells = boardElement.querySelectorAll(".cell");
  cells.forEach((cell) => {
    const row = Number(cell.dataset.row);
    const col = Number(cell.dataset.column);
    const value = boardState[row][col];

    cell.dataset.player = value ? String(value) : "";
    cell.removeAttribute("data-win");
    cell.ariaLabel = value
      ? `Cel (${row + 1}, ${col + 1}) bezet door speler ${value === 1 ? "Rood" : "Geel"}`
      : `Lege cel (${row + 1}, ${col + 1})`;
  });
}

function isBoardFull() {
  return boardState.every((row) => row.every((cell) => cell !== 0));
}

function directions() {
  return [
    [0, 1],
    [1, 0],
    [1, 1],
    [1, -1],
  ];
}

function checkWin(row, col) {
  const player = boardState[row][col];

  for (const [dx, dy] of directions()) {
    const cells = [[row, col]];

    let r = row + dx;
    let c = col + dy;
    while (isInside(r, c) && boardState[r][c] === player) {
      cells.push([r, c]);
      r += dx;
      c += dy;
    }

    r = row - dx;
    c = col - dy;
    while (isInside(r, c) && boardState[r][c] === player) {
      cells.unshift([r, c]);
      r -= dx;
      c -= dy;
    }

    if (cells.length >= 4) {
      return cells;
    }
  }

  return null;
}

function isInside(row, col) {
  return row >= 0 && row < ROWS && col >= 0 && col < COLS;
}

function highlightWinningCells(cells) {
  cells.forEach(([row, col]) => {
    const selector = `.cell[data-row="${row}"][data-column="${col}"]`;
    const cell = boardElement.querySelector(selector);
    if (cell) {
      cell.dataset.win = "true";
    }
  });
}

function resetGame() {
  boardState = createEmptyBoard();
  currentPlayer = 1;
  gameOver = false;
  paintBoard();
  updateTurnIndicator();
}

resetButton.addEventListener("click", resetGame);

setupBoard();
resetGame();
