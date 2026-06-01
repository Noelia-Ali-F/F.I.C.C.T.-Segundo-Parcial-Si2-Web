import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

type PlanCard = {
  name: string;
  subtitle?: string;
  description: string;
  benefits: string[];
  badge?: string;
  cta: string;
  theme?: 'highlight' | 'dark';
};

@Component({
  selector: 'app-planes-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="page">
      <section class="section plans-showcase">
        <div class="plans-showcase-top">
          <div class="plans-showcase-copy">
            <h2>Planes para talleres asociados</h2>
            <p>
              Elige como quieres crecer dentro de la red de asistencia vehicular.
            </p>
            <p>Mas visibilidad, mas solicitudes, mas ingresos.</p>
          </div>

          <article class="plans-promo-card">
            <div class="plans-promo-check">✓</div>
            <div>
              <h3>No pagas por estar... Ganas por trabajar.</h3>
              <p>La plataforma te conecta con clientes reales que necesitan ayuda ahora.</p>
            </div>
          </article>
        </div>

        <div class="plans-grid">
          <article
            class="plan-card showcase-plan-card"
            *ngFor="let plan of plans"
            [class.plan-highlight]="plan.theme === 'highlight'"
            [class.plan-dark]="plan.theme === 'dark'"
          >
            <span class="plan-badge" *ngIf="plan.badge">{{ plan.badge }}</span>
            <h3>{{ plan.name }}</h3>
            <p class="plan-tagline" *ngIf="plan.subtitle">{{ plan.subtitle }}</p>
            <p class="plan-target" *ngIf="plan.description">{{ plan.description }}</p>

            <ul class="plan-benefits">
              <li *ngFor="let benefit of plan.benefits">{{ benefit }}</li>
            </ul>

            <a class="button primary plan-cta" routerLink="/contacto">{{ plan.cta }}</a>
          </article>
        </div>
      </section>
    </main>
  `,
  styleUrl: '../shared/shared-pages.css',
})
export class PlanesPageComponent {
  readonly plans: PlanCard[] = [
    {
      name: 'Plan Base',
      badge: 'Gratis',
      description: 'Empieza sin costo y recibe tus primeras solicitudes.',
      benefits: [
        'Perfil dentro de la plataforma',
        'Visibilidad limitada: hasta 4 solicitudes por dia',
        'Recepcion de consultas basicas',
        'Participacion en la red de talleres',
        'Comision por servicio: 10%',
      ],
      cta: 'Empezar gratis',
    },
    {
      name: 'Plan Profesional',
      badge: 'Recomendado',
      description: 'Aumenta tu visibilidad y recibe mas trabajos.',
      benefits: [
        'Mayor prioridad en asignaciones',
        'Mas visibilidad dentro de la plataforma',
        'Mas solicitudes por dia',
        'Posicionamiento destacado',
        'Comision reducida',
      ],
      cta: 'Quiero este plan',
      theme: 'highlight',
    },
    {
      name: 'Plan Aliado 24/7',
      subtitle: 'Para talleres con atencion continua y mayor capacidad operativa.',
      description: '',
      benefits: [
        'Atencion prioritaria en emergencias',
        'Participacion en servicios urgentes',
        'Operacion 24/7',
        'Maxima visibilidad',
        'Acceso inmediato a solicitudes criticas',
        'Comision aun menor',
      ],
      cta: 'Unirme como aliado',
      theme: 'dark',
    },
  ];
}
