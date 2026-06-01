import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-alert-success',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="alert-success" role="status" aria-live="polite">
      <strong>{{ title }}</strong>
      <p>{{ message }}</p>
    </section>
  `,
  styles: [
    `
      .alert-success {
        display: grid;
        gap: 0.35rem;
        position: fixed;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        z-index: 1200;
        width: min(25rem, calc(100vw - 2rem));
        margin: 0;
        padding: 1rem 1.1rem;
        border-radius: 18px;
        color: #14532d;
        background: rgba(246, 255, 248, 0.97);
        border: 1px solid rgba(34, 197, 94, 0.28);
        box-shadow: 0 18px 38px rgba(18, 66, 40, 0.16);
        backdrop-filter: blur(10px);
        font-size: 0.92rem;
        line-height: 1.45;
      }

      .alert-success strong {
        font-size: 1rem;
      }

      .alert-success p {
        margin: 0;
        font-weight: 600;
      }
    `,
  ],
})
export class AlertSuccessComponent {
  @Input({ required: true }) title!: string;
  @Input({ required: true }) message!: string;
}
