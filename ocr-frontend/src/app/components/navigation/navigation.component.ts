import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-navigation',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './navigation.component.html',
  styleUrls: ['./navigation.component.css']
})
export class NavigationComponent {
  showProfileModal = false;

  constructor(
    public authService: AuthService,
    public router: Router
  ) {}

  toggleProfileModal(): void {
    this.showProfileModal = !this.showProfileModal;
  }

  logout(): void {
    this.showProfileModal = false;
    this.authService.logout();
    this.router.navigate(['/login']);
  }
}
