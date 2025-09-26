import { CommonModule } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';

type Player = 1 | 2;

type Cell = 0 | Player;

interface MovePosition {
  row: number;
  col: number;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AppComponent {
  readonly rows = 6;
  readonly columns = 7;

  readonly columnIndices = Array.from({ length: this.columns }, (_, index) => index);
  readonly rowIndices = Array.from({ length: this.rows }, (_, index) => index);

  readonly board = signal<Cell[][]>(this.createEmptyBoard());
  readonly currentPlayer = signal<Player>(1);
  readonly winner = signal<Player | null>(null);
  readonly isDraw = signal(false);
  readonly lastMove = signal<MovePosition | null>(null);
  readonly hoverColumn = signal<number | null>(null);

  readonly statusMessage = computed(() => {
    if (this.winner()) {
      return `Speler ${this.describePlayer(this.winner())} heeft gewonnen!`;
    }

    if (this.isDraw()) {
      return 'Het is een gelijkspel!';
    }

    return `Speler ${this.describePlayer(this.currentPlayer())} is aan zet.`;
  });

  dropDisc(column: number): void {
    if (this.winner() || this.isDraw()) {
      return;
    }

    const targetRow = this.findAvailableRow(column);

    if (targetRow === null) {
      return;
    }

    const nextBoard = this.board().map((row) => [...row]) as Cell[][];
    nextBoard[targetRow][column] = this.currentPlayer();
    this.board.set(nextBoard);
    this.lastMove.set({ row: targetRow, col: column });

    if (this.hasPlayerWon(targetRow, column)) {
      this.winner.set(this.currentPlayer());
      return;
    }

    if (this.board().every((row) => row.every((cell) => cell !== 0))) {
      this.isDraw.set(true);
      return;
    }

    this.currentPlayer.set(this.currentPlayer() === 1 ? 2 : 1);
  }

  setHoveredColumn(column: number | null): void {
    if (this.winner() || this.isDraw()) {
      this.hoverColumn.set(null);
      return;
    }

    if (column === null || this.isColumnFull(column)) {
      this.hoverColumn.set(null);
      return;
    }

    this.hoverColumn.set(column);
  }

  resetGame(): void {
    this.board.set(this.createEmptyBoard());
    this.currentPlayer.set(1);
    this.winner.set(null);
    this.isDraw.set(false);
    this.lastMove.set(null);
    this.hoverColumn.set(null);
  }

  isColumnFull(column: number): boolean {
    return this.findAvailableRow(column) === null;
  }

  isColumnDisabled(column: number): boolean {
    return this.winner() !== null || this.isDraw() || this.isColumnFull(column);
  }

  canPreview(row: number, column: number): boolean {
    if (this.winner() || this.isDraw()) {
      return false;
    }

    if (this.hoverColumn() !== column) {
      return false;
    }

    const availableRow = this.findAvailableRow(column);
    return availableRow === row;
  }

  getCellState(row: number, column: number): Cell {
    return this.board()[row][column];
  }

  isLastMove(row: number, column: number): boolean {
    const last = this.lastMove();
    return !!last && last.row === row && last.col === column;
  }

  private hasPlayerWon(row: number, column: number): boolean {
    const player = this.board()[row][column];

    const directions: Array<[rowOffset: number, colOffset: number]> = [
      [0, 1],
      [1, 0],
      [1, 1],
      [1, -1]
    ];

    return directions.some(([rowOffset, colOffset]) =>
      this.countConnected(row, column, rowOffset, colOffset, player) +
        this.countConnected(row, column, -rowOffset, -colOffset, player) -
        1 >=
      4
    );
  }

  private countConnected(
    row: number,
    column: number,
    rowOffset: number,
    colOffset: number,
    player: Cell
  ): number {
    let count = 0;
    let currentRow = row;
    let currentColumn = column;

    while (this.isInsideBoard(currentRow, currentColumn) && this.board()[currentRow][currentColumn] === player) {
      count += 1;
      currentRow += rowOffset;
      currentColumn += colOffset;
    }

    return count;
  }

  private isInsideBoard(row: number, column: number): boolean {
    return row >= 0 && row < this.rows && column >= 0 && column < this.columns;
  }

  private findAvailableRow(column: number): number | null {
    for (let row = this.rows - 1; row >= 0; row -= 1) {
      if (this.board()[row][column] === 0) {
        return row;
      }
    }

    return null;
  }

  private createEmptyBoard(): Cell[][] {
    return Array.from({ length: this.rows }, () =>
      Array.from({ length: this.columns }, () => 0 as Cell)
    );
  }

  private describePlayer(player: Player | null): string {
    switch (player) {
      case 1:
        return 'Rood';
      case 2:
        return 'Geel';
      default:
        return '';
    }
  }
}
