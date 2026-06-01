import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';

type ValidationDialogData = {
  missingFields: string[];
};

@Component({
  selector: 'app-validation-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule],
  template: `
    <section class="validation-dialog">
      <h2 mat-dialog-title>Completa los campos obligatorios</h2>

      <div mat-dialog-content>
        <p>Faltan los siguientes datos antes de registrar el taller:</p>
        <ul>
          <li *ngFor="let field of data.missingFields">{{ field }}</li>
        </ul>
      </div>

      <div mat-dialog-actions align="end">
        <button mat-flat-button color="primary" (click)="close()">Entendido</button>
      </div>
    </section>
  `,
  styles: [
    `
      .validation-dialog {
        color: #183261;
      }

      h2 {
        margin: 0;
        font-size: 1.2rem;
        font-weight: 800;
      }

      p {
        margin: 0 0 0.8rem;
        line-height: 1.5;
      }

      ul {
        margin: 0;
        padding-left: 1.2rem;
      }

      li {
        margin: 0.3rem 0;
        font-weight: 700;
      }
    `,
  ],
})
export class ValidationDialogComponent {
  readonly data = inject<ValidationDialogData>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ValidationDialogComponent>);

  close(): void {
    this.dialogRef.close();
  }
}
