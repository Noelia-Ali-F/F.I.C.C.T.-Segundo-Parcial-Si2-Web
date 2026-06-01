import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-not-found-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <main class="page not-found">
      <p class="eyebrow">404</p>
      <h1>Página no encontrada</h1>
      <p class="lead">
        La ruta que buscabas no existe todavía o fue movida dentro de esta propuesta de frontend.
      </p>
      <a class="button primary" routerLink="/">Volver al inicio</a>
    </main>
  `,
  styleUrl: '../shared/shared-pages.css',
})
export class NotFoundPageComponent {}
