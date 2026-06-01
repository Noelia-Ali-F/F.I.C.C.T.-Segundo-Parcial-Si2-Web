import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule, NgForm } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import { API_BASE_URL } from '../shared/api-base';
import { ValidationDialogComponent } from '../shared/validation-dialog.component';

@Component({
  selector: 'app-forgot-password-page',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, RouterLink],
  template: `
    <main class="page login-clean-page forgot-password-page">
      <section class="login-clean-shell">
        <div class="login-clean-card">
          <div class="login-clean-art">
            <img src="/hero-grua-scene.svg" alt="Recuperación de contraseña" />
          </div>

          <article class="login-clean-form-card">
            <span class="forgot-password-eyebrow">Soporte de acceso</span>
            <h1>{{ pageTitle }}</h1>
            <p class="forgot-password-copy">
              {{ pageCopy }}
            </p>

            <p class="login-clean-feedback" *ngIf="showWorkshopResetMessage">
              Detectamos un ingreso con contraseña temporal. Antes de acceder al sistema, debes registrar una nueva contraseña para el correo indicado.
            </p>

            <!--
              AQUI ESTA EL FORMULARIO DE RECUPERACION Y CAMBIO DE CONTRASENA
            -->
            <form class="login-clean-form" (ngSubmit)="submitRecovery(recoveryForm)" #recoveryForm="ngForm">
              <label class="form-field">
                <span>Correo electrónico</span>
                <input
                  type="email"
                  name="email"
                  [(ngModel)]="email"
                  required
                  email
                  placeholder="ejemplo@talleracb.com"
                />
              </label>

              <label class="form-field">
                <span>Nueva contraseña</span>
                <span class="password-field">
                  <input
                    [type]="showNewPassword ? 'text' : 'password'"
                    name="newPassword"
                    [(ngModel)]="newPassword"
                    required
                    minlength="6"
                    placeholder="Ingresa tu nueva contraseña"
                  />
                  <button
                    class="password-toggle"
                    type="button"
                    (click)="showNewPassword = !showNewPassword"
                    [attr.aria-label]="showNewPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                  >
                    {{ showNewPassword ? '🙈' : '👁' }}
                  </button>
                </span>
              </label>

              <label class="form-field">
                <span>Confirmar nueva contraseña</span>
                <span class="password-field">
                  <input
                    [type]="showConfirmPassword ? 'text' : 'password'"
                    name="confirmPassword"
                    [(ngModel)]="confirmPassword"
                    required
                    minlength="6"
                    placeholder="Confirma tu nueva contraseña"
                  />
                  <button
                    class="password-toggle"
                    type="button"
                    (click)="showConfirmPassword = !showConfirmPassword"
                    [attr.aria-label]="showConfirmPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
                  >
                    {{ showConfirmPassword ? '🙈' : '👁' }}
                  </button>
                </span>
              </label>

              <p class="login-clean-feedback" *ngIf="submitMessage">{{ submitMessage }}</p>

              <button class="button primary login-clean-submit" type="submit">
                Cambiar contraseña
              </button>

              <a class="login-clean-option forgot-password-back" routerLink="/login">
                Volver al inicio de sesión
              </a>
            </form>
          </article>
        </div>
      </section>
    </main>
  `,
  styleUrl: '../shared/shared-pages.css',
})
export class ForgotPasswordPageComponent {
  private readonly dialog = inject(MatDialog);
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  private readonly workshopsChangePasswordApiUrl = `${API_BASE_URL}/workshops/change-password`;
  private readonly workshopsForgotPasswordApiUrl = `${API_BASE_URL}/workshops/forgot-password`;
  private readonly clientsForgotPasswordApiUrl = `${API_BASE_URL}/clientes/forgot-password`;

  email = '';
  newPassword = '';
  confirmPassword = '';
  showNewPassword = false;
  showConfirmPassword = false;
  submitMessage = '';
  showWorkshopResetMessage = false;
  isSubmitting = false;

  get pageTitle(): string {
    return this.showWorkshopResetMessage ? 'Registrar nueva contraseña' : '¿Olvidaste tu contraseña?';
  }

  get pageCopy(): string {
    return this.showWorkshopResetMessage
      ? 'Registra una nueva contraseña para el taller antes de continuar con el inicio de sesión.'
      : 'Ingresa tu correo electrónico y registra una nueva contraseña para recuperar el acceso como cliente o taller.';
  }

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      this.email = params.get('email')?.trim() ?? '';
      this.showWorkshopResetMessage = params.get('source') === 'workshop-initial-login';
    });
  }

  submitRecovery(recoveryForm: NgForm): void {
    if (this.isSubmitting) {
      return;
    }

    const missingFields: string[] = [];
    const normalizedEmail = this.email.trim();

    if (!normalizedEmail) {
      missingFields.push('Correo Electrónico');
    } else if (!this.emailPattern.test(normalizedEmail)) {
      missingFields.push('Correo Electrónico válido');
    }

    if (!this.newPassword.trim()) {
      missingFields.push('Nueva Contraseña');
    } else if (this.newPassword.trim().length < 6) {
      missingFields.push('Nueva Contraseña de al menos 6 caracteres');
    }

    if (!this.confirmPassword.trim()) {
      missingFields.push('Confirmar Nueva Contraseña');
    } else if (this.newPassword !== this.confirmPassword) {
      missingFields.push('Confirmación de contraseña válida');
    }

    if (missingFields.length > 0 || recoveryForm.invalid) {
      this.submitMessage = 'Completa correctamente el correo y las contraseñas para continuar.';
      this.dialog.open(ValidationDialogComponent, {
        width: '26rem',
        maxWidth: 'calc(100vw - 2rem)',
        data: { missingFields },
      });
      return;
    }

    this.isSubmitting = true;
    this.submitMessage = '';

    const payload = {
      email: normalizedEmail.toLowerCase(),
      newPassword: this.newPassword.trim(),
      confirmPassword: this.confirmPassword.trim(),
    };

    if (this.showWorkshopResetMessage) {
      this.http
        .post<{ message: string }>(this.workshopsChangePasswordApiUrl, payload)
        .subscribe({
          next: async (response) => {
            this.isSubmitting = false;
            this.submitMessage = response.message;
            recoveryForm.resetForm({
              email: normalizedEmail,
              newPassword: '',
              confirmPassword: '',
            });
            await this.router.navigate(['/login']);
          },
          error: (error: HttpErrorResponse) => {
            this.isSubmitting = false;
            this.submitMessage = error.error?.detail || 'No se pudo actualizar la contraseña.';
          },
        });
      return;
    }

    this.http
      .post<{ message: string }>(this.clientsForgotPasswordApiUrl, payload)
      .subscribe({
        next: async (response) => {
          this.isSubmitting = false;
          this.submitMessage = response.message;
          recoveryForm.resetForm({
            email: normalizedEmail,
            newPassword: '',
            confirmPassword: '',
          });
          await this.router.navigate(['/login']);
        },
        error: (clientError: HttpErrorResponse) => {
          if (clientError.status !== 404) {
            this.isSubmitting = false;
            this.submitMessage = clientError.error?.detail || 'No se pudo actualizar la contraseña.';
            return;
          }

          this.http
            .post<{ message: string }>(this.workshopsForgotPasswordApiUrl, payload)
            .subscribe({
              next: async (response) => {
                this.isSubmitting = false;
                this.submitMessage = response.message;
                recoveryForm.resetForm({
                  email: normalizedEmail,
                  newPassword: '',
                  confirmPassword: '',
                });
                await this.router.navigate(['/login']);
              },
              error: (workshopError: HttpErrorResponse) => {
                this.isSubmitting = false;
                this.submitMessage = workshopError.error?.detail || 'No se pudo actualizar la contraseña.';
              },
            });
        },
      });
  }
}
