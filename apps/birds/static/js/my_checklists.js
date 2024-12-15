const { createApp } = Vue;
createApp({
    data() {
        return {
            checklists: [],
            searchQuery: '',
            editForm: {
                id: null,
                COMMON_NAME: '',
                LATITUDE: '',
                LONGITUDE: '',
                OBSERVATION_DATE: '',
                OBSERVATION_TIME: '', // Add time field
                species_count: 0
            },
            showModal: false
        };
    },
    computed: {
        filteredChecklists() {
            return this.checklists.filter(checklist =>
                checklist.COMMON_NAME.toLowerCase().includes(this.searchQuery.toLowerCase())
            );
        }
    },
    methods: {
      async fetchChecklists() {
        try {
            const response = await axios.get('/birds/get_my_checklists');
            const checklistsWithDetails = await Promise.all(
                response.data.checklists.map(async (checklist) => {
                    try {
                        const speciesCountResponse = await axios.get('/birds/get_checklist_species_count', {
                            params: { checklist_id: checklist.id }
                        });
    
                        return {
                            ...checklist,
                            species_count: speciesCountResponse.data.total_observations || 0,
                            DURATION_MINUTES: checklist.DURATION_MINUTES || 0
                        };
                    } catch (error) {
                        console.error(`Detailed error for checklist ${checklist.id}:`, error.response || error);
                        return { 
                            ...checklist, 
                            species_count: 0,
                            DURATION_MINUTES: 0
                        };
                    }
                })
            );
            this.checklists = checklistsWithDetails;
        } catch (error) {
            console.error('Error fetching checklists:', error);
        }
    },
        extractTimeFromDate(dateString) {
            // Extract time from a date string or return a default time
            if (!dateString) return '00:00';
            try {
                const date = new Date(dateString);
                return date.toTimeString().slice(0, 5);
            } catch {
                return '00:00';
            }
        },
        async deleteChecklist(id) {
            try {
                const response = await axios.delete(`/birds/delete_checklist/${id}`);
                if (response.data.status === 'success') {
                    this.checklists = this.checklists.filter(checklist => checklist.id !== id);
                }
            } catch (error) {
                console.error('Error deleting checklist:', error);
            }
        },
        addNewChecklist() {
            window.location.href = '/birds/add_checklist';
        },
        editChecklist(index) {
          const checklist = this.checklists[index];
          this.editForm = {
              ...checklist,
              OBSERVATION_DATE: this.formatDateForInput(checklist.OBSERVATION_DATE),
              OBSERVATION_TIME: this.extractTimeFromDate(checklist.OBSERVATION_DATE),
              DURATION_MINUTES: checklist.DURATION_MINUTES || 0
          };
          this.showModal = true;
      },

        formatDateForInput(dateString) {
            // Convert datestring to YYYY-MM-DD format for date input
            if (!dateString) return '';
            return new Date(dateString).toISOString().split('T')[0];
        },
        closeModal() {
            this.showModal = false;
        },
       async submitEdit() {
          try {
              // Combine date and time for submission
              const combinedDateTime = `${this.editForm.OBSERVATION_DATE}T${this.editForm.OBSERVATION_TIME}:00`;
              
              const submissionData = {
                  ...this.editForm,
                  OBSERVATION_DATE: combinedDateTime
              };


                const response = await axios.post(`/birds/edit_checklist/${this.editForm.id}`, submissionData);
                if (response.data.status === 'success') {
                    // Update the checklist in the local array
                    const index = this.checklists.findIndex(c => c.id === this.editForm.id);
                    if (index !== -1) {
                        // Preserve the existing species_count when updating
                        this.checklists[index] = {
                            ...submissionData,
                            species_count: this.checklists[index].species_count
                        };
                    }
                    this.closeModal();
                }
            } catch (error) {
                console.error('Error editing checklist:', error);
            }
        }
    },
    mounted() {
        this.fetchChecklists();
    }
}).mount('#app');