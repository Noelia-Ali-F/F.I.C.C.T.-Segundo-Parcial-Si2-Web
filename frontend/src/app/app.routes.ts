import { Routes } from '@angular/router';

import { authGuard } from './auth/auth.guard';
import { ForgotPasswordPageComponent } from './auth/forgot-password.component';
import { LoginPageComponent } from './auth/login.component';
import { DashboardPageComponent } from './dashboard/dashboard-page.component';
import { OfflineEmergenciesListComponent } from './emergencias/offline-emergencies-list.component';
import { OfflineEmergencyFormComponent } from './emergencias/offline-emergency-form.component';
import { HomePageComponent } from './inicio/home.component';
import { MapPageComponent } from './inicio/mapa.component';
import { NotFoundPageComponent } from './inicio/not-found.component';
import { PlanesPageComponent } from './inicio/planes.component';
import { SectionPageComponent } from './inicio/section.component';
import { ServiciosPageComponent } from './inicio/servicios.component';

export const appRoutes: Routes = [
  {
    path: '',
    component: HomePageComponent,
    title: 'Inicio | Automóvil Club Boliviano',
  },
  {
    path: 'suscripciones',
    redirectTo: 'planes',
    pathMatch: 'full',
  },
  {
    path: 'nosotros',
    redirectTo: 'planes',
    pathMatch: 'full',
  },
  {
    path: 'planes',
    component: PlanesPageComponent,
    title: 'Planes | Talleres Socios',
  },
  {
    path: 'novedades',
    redirectTo: 'planes',
    pathMatch: 'full',
  },
  {
    path: 'servicios',
    component: ServiciosPageComponent,
    title: 'Servicios | Asistencia y Auxilio',
  },
  {
    path: 'mapa',
    component: MapPageComponent,
    title: 'Mapa | Santa Cruz de la Sierra',
  },
  {
    path: 'login',
    component: LoginPageComponent,
    title: 'Iniciar sesión | Taller ACB Asistencia',
  },
  {
    path: 'forgot-password',
    component: ForgotPasswordPageComponent,
    title: 'Recuperar contraseña | Taller ACB Asistencia',
  },
  {
    path: 'dashboard',
    component: DashboardPageComponent,
    canActivate: [authGuard],
    title: 'Dashboard | Taller ACB Asistencia',
  },
  {
    path: 'escuela',
    redirectTo: 'mapa',
    pathMatch: 'full',
  },
  {
    path: 'emergencias-offline',
    component: OfflineEmergenciesListComponent,
    title: 'Emergencias offline | Automóvil Club Boliviano',
  },
  {
    path: 'emergencias-offline/nueva',
    component: OfflineEmergencyFormComponent,
    title: 'Registrar emergencia offline | Automóvil Club Boliviano',
  },
  {
    path: 'contacto',
    component: SectionPageComponent,
    data: { section: 'contacto' },
    title: 'Contacto | Automóvil Club Boliviano',
  },
  {
    path: '**',
    component: NotFoundPageComponent,
    title: 'Página no encontrada',
  },
];
