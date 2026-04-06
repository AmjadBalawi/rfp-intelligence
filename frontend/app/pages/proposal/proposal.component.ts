import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ProposalService } from '../../services/proposal.service';

@Component({
  selector: 'app-proposal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './proposal.component.html',
  styleUrls: ['./proposal.component.scss']
})
export class ProposalComponent {
  rfpText = '';
  loading = false;
  activeTab = 'pipeline';

  pipelineEvents: any[] = [];
  retrievedProducts: any[] = [];
  proposalBlocks: any[] = [];
  evaluation: any = null;

  constructor(
    private proposalService: ProposalService,
    private cdr: ChangeDetectorRef
  ) {}

  onSubmit() {
    if (!this.rfpText.trim() || this.loading) return;

    // Reset state
    this.pipelineEvents = [];
    this.retrievedProducts = [];
    this.proposalBlocks = [];
    this.evaluation = null;
    this.loading = true;
    this.activeTab = 'pipeline';
    this.cdr.detectChanges();

    const timeout = setTimeout(() => {
      if (this.loading) {
        this.loading = false;
        this.cdr.detectChanges();
        console.warn('Loading stopped by timeout');
      }
    }, 60000);

    this.proposalService.generateProposal(this.rfpText).subscribe({
      next: (event: any) => {
        console.log('📦 Event received:', event);

        if (event?.node && event.state) {
          this.pipelineEvents.push({ node: event.node, state: event.state });

          switch (event.node) {
            case 'retrieve':
              if (event.state.retrieved_products) {
                this.retrievedProducts = [...event.state.retrieved_products];
                this.activeTab = 'retrieval';
                this.cdr.detectChanges();
              }
              break;

            case 'generate':
              if (event.state.generated_blocks) {
                this.proposalBlocks = [...event.state.generated_blocks];
                this.activeTab = 'proposal';
                console.log('✅ Proposal blocks loaded:', this.proposalBlocks.length);
                this.cdr.detectChanges();
              }
              break;

            case 'evaluate':
              if (event.state.evaluation) {
                this.evaluation = event.state.evaluation;
                this.activeTab = 'evaluation';
                // Stop loading and show success
                this.loading = false;
                clearTimeout(timeout);
                this.cdr.detectChanges();
                // Alert is fine – after dismissing, button is clickable because loading is false
                alert('✅ Proposal generated successfully!');
              }
              break;

            default:
              console.log(`📌 Pipeline node: ${event.node}`);
          }
        }
      },
      error: (err) => {
        console.error('❌ Generation error:', err);
        this.loading = false;
        clearTimeout(timeout);
        alert('Failed to generate proposal. Check console.');
        this.cdr.detectChanges();
      },
      complete: () => {
        console.log('🏁 Stream completed');
        // Only reset loading if it wasn't already reset by 'evaluate' event
        if (this.loading) {
          this.loading = false;
          clearTimeout(timeout);
          this.cdr.detectChanges();
        }
      }
    });
  }

  seed() {
    this.proposalService.seedCatalog()
      .then(res => {
        console.log('Catalog seeded:', res);
        alert('Catalog seeded successfully');
      })
      .catch(err => {
        console.error('Seed error:', err);
        alert('Failed to seed catalog');
      });
  }
}
