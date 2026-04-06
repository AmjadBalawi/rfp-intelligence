onSubmit() {
  if (!this.rfpText.trim() || this.loading) return;

  // Reset state
  this.pipelineEvents = [];
  this.retrievedProducts = [];
  this.proposalBlocks = [];
  this.evaluation = null;
  this.loading = true;
  this.activeTab = 'pipeline';

  const timeout = setTimeout(() => {
    if (this.loading) {
      this.loading = false;
      console.warn('Loading stopped by timeout');
    }
  }, 60000);

  this.proposalService.generateProposal(this.rfpText).subscribe({
    next: (event: any) => {
      console.log('Component received:', event); // Debug

      // Handle pipeline step (every event has node and state)
      if (event.node && event.state !== undefined) {
        this.pipelineEvents.push({ node: event.node, state: event.state });

        // Extract data based on node type
        switch (event.node) {
          case 'retrieve':
            if (event.state.retrieved_products) {
              this.retrievedProducts = event.state.retrieved_products;
              this.activeTab = 'retrieval';
            }
            break;
          case 'generate':
            if (event.state.generated_blocks) {
              this.proposalBlocks = event.state.generated_blocks;
              this.activeTab = 'proposal';
              console.log('Proposal blocks loaded:', this.proposalBlocks.length);
            }
            break;
          case 'evaluate':
            if (event.state.evaluation) {
              this.evaluation = event.state.evaluation;
              this.activeTab = 'evaluation';
              this.loading = false;
              clearTimeout(timeout);
              alert('✅ Proposal generated successfully!');
            }
            break;
          default:
            // Other nodes (extract, plan_proposal, create_proposal) – just log
            console.log('Pipeline step:', event.node);
        }
      } else {
        console.warn('Unexpected event format:', event);
      }
    },
    error: (err) => {
      console.error('Generation error:', err);
      this.loading = false;
      clearTimeout(timeout);
      alert('Failed to generate proposal.');
    },
    complete: () => {
      console.log('Stream completed');
      if (this.loading) {
        this.loading = false;
        clearTimeout(timeout);
      }
    }
  });
}
