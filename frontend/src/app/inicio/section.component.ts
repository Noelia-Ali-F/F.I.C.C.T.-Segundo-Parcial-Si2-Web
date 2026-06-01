import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { sectionContent } from '../shared/site-content';

@Component({
  selector: 'app-section-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="page">
      <ng-container *ngIf="isContactSection; else defaultSection">
        <section class="contact-showcase">
          <div class="contact-showcase-copy">
            <p class="eyebrow">Contacto</p>
            <h1>Atención clara y accesible</h1>
            <p class="lead">
              Estamos aqui para ayudarte. Contactanos de forma rapida y sencilla.
            </p>
          </div>

          <div class="contact-showcase-grid">
            <article class="contact-reasons-card">
              <h2>¿Por qué contactar con nosotros?</h2>
              <span class="contact-divider"></span>

              <ul class="contact-reasons-list">
                <li *ngFor="let reason of contactReasons">
                  <span class="contact-check">✓</span>
                  <span>{{ reason }}</span>
                </li>
              </ul>
            </article>

            <aside class="contact-info-panel">
              <h2>Información de Contacto</h2>

              <div class="contact-info-list">
                <div class="contact-info-item">
                  <span class="contact-info-icon">✉</span>
                  <span>info@talleracb.com</span>
                </div>

                <div class="contact-info-item">
                  <span class="contact-info-icon contact-info-icon-gold">◔</span>
                  <span>Disponible 24/7</span>
                </div>
              </div>

              <a class="contact-whatsapp-button" href="https://wa.me/591800163316" target="_blank" rel="noreferrer">
                <span class="contact-whatsapp-icon">W</span>
                <span>Escríbenos por WhatsApp</span>
              </a>

              <a class="contact-call-button" href="tel:800163316">
                Llámanos ahora
                <strong>800163316</strong>
              </a>
            </aside>
          </div>
        </section>
      </ng-container>

      <ng-template #defaultSection>
        <section class="section-hero">
          <p class="eyebrow">{{ content.eyebrow }}</p>
          <h1>{{ content.title }}</h1>
          <p class="lead">{{ content.intro }}</p>
        </section>

        <section class="spotlight compact">
          <div>
            <h2>Cómo está pensada esta vista</h2>
            <p>{{ content.lead }}</p>
          </div>

          <div class="quote-card">
            <p>{{ content.highlight }}</p>
          </div>
        </section>

        <section class="section">
          <div class="card-grid">
            <article class="info-card" *ngFor="let card of content.cards">
              <h3>{{ card.title }}</h3>
              <p>{{ card.description }}</p>
              <small *ngIf="card.detail">{{ card.detail }}</small>
            </article>
          </div>
        </section>

        <section class="closing-banner">
          <div>
            <p class="eyebrow">Siguiente paso</p>
            <h2>{{ content.cta }}</h2>
          </div>
          <a class="button primary" routerLink="/contacto">Ir a contacto</a>
        </section>
      </ng-template>
    </main>
  `,
  styleUrl: '../shared/shared-pages.css',
})
export class SectionPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly sectionKey = (this.route.snapshot.data['section'] as string) ?? 'nosotros';

  readonly content =
    sectionContent[this.sectionKey] ??
    sectionContent['nosotros'];

  readonly isContactSection = this.sectionKey === 'contacto';

  readonly contactReasons = [
    'Respuesta rapida en menos de 30 minutos',
    'Atencion disponible 24/7, incluso en dias festivos',
    'Talleres y tecnicos certificados y profesionales',
    'Cobertura en toda la ciudad y alrededores',
    'Precios claros sin costos ocultos',
  ];
}
