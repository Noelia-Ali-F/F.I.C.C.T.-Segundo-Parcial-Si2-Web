import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  private readonly router = inject(Router);

  readonly navigation = [
    { label: 'Inicio', path: '/' },
    { label: 'Servicios', path: '/servicios' },
    { label: 'Planes', path: '/planes' },
    { label: 'Mapa', path: '/mapa' },
    { label: 'Contacto', path: '/contacto' },
  ];

  readonly isAuthRoute$ = this.router.events.pipe(
    filter((event): event is NavigationEnd => event instanceof NavigationEnd),
    map(
      (event) =>
        event.urlAfterRedirects.startsWith('/login') ||
        event.urlAfterRedirects.startsWith('/forgot-password') ||
        event.urlAfterRedirects.startsWith('/dashboard'),
    ),
    startWith(
      this.router.url.startsWith('/login') ||
        this.router.url.startsWith('/forgot-password') ||
        this.router.url.startsWith('/dashboard'),
    ),
  );
}
