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
                OBSERVATION_TIME: '',
                species_count: 0
            },
            showModal: false,
            showSpeciesModal: false,
            selectedSpecies: {},
            uniqueSpecies: [],
            speciesTrendChart: null,
            speciesMap: null
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
                this.processUniqueSpecies();
                this.createOverallTrendChart();
            } catch (error) {
                console.error('Error fetching checklists:', error);
            }
        },
        processUniqueSpecies() {
            // Get unique species with their first and last observation dates
            const speciesMap = new Map();
            this.checklists.forEach(checklist => {
                if (!speciesMap.has(checklist.COMMON_NAME)) {
                    speciesMap.set(checklist.COMMON_NAME, {
                        firstObservation: new Date(checklist.OBSERVATION_DATE),
                        lastObservation: new Date(checklist.OBSERVATION_DATE),
                        observations: [checklist]
                    });
                } else {
                    const speciesData = speciesMap.get(checklist.COMMON_NAME);
                    const observationDate = new Date(checklist.OBSERVATION_DATE);
                    
                    // Update first and last observation dates
                    if (observationDate < speciesData.firstObservation) {
                        speciesData.firstObservation = observationDate;
                    }
                    if (observationDate > speciesData.lastObservation) {
                        speciesData.lastObservation = observationDate;
                    }
                    
                    speciesData.observations.push(checklist);
                }
            });

            // Convert map to array of unique species
            this.uniqueSpecies = Array.from(speciesMap, ([name, data]) => ({
                name,
                firstObservation: data.firstObservation,
                lastObservation: data.lastObservation,
                observations: data.observations
            })).sort((a, b) => b.observations.length - a.observations.length);
        },
        createOverallTrendChart() {
            // Prepare data for trend chart
            const monthlyObservations = {};
            this.checklists.forEach(checklist => {
                const date = new Date(checklist.OBSERVATION_DATE);
                const monthKey = `${date.getFullYear()}-${date.getMonth() + 1}`;
                monthlyObservations[monthKey] = (monthlyObservations[monthKey] || 0) + 1;
            });

            // Sort monthly observations chronologically
            const sortedMonths = Object.keys(monthlyObservations).sort();
            const chartData = {
                labels: sortedMonths,
                datasets: [{
                    label: 'Number of Checklists',
                    data: sortedMonths.map(month => monthlyObservations[month]),
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            };

            // Create chart after a short delay to ensure DOM is ready
            this.$nextTick(() => {
                const ctx = document.getElementById('overall-trend-chart');
                if (ctx) {
                    this.overallTrendChart = new Chart(ctx, {
                        type: 'line',
                        data: chartData,
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: true,
                                    text: 'Bird Watching Trend Over Time'
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Number of Checklists'
                                    }
                                },
                                x: {
                                    title: {
                                        display: true,
                                        text: 'Month'
                                    }
                                }
                            }
                        }
                    });
                }
            });
        },
        showSpeciesDetails(species) {
            this.selectedSpecies = species;
            this.showSpeciesModal = true;
        
            // Create species trend chart
            this.$nextTick(() => {
                const ctx = document.getElementById('species-trend-chart');
                if (ctx) {
                    // Prepare data for species trend chart
                    const monthlyObservations = {};
                    species.observations.forEach(obs => {
                        const date = new Date(obs.OBSERVATION_DATE);
                        const monthKey = `${date.getFullYear()}-${date.getMonth() + 1}`;
                        monthlyObservations[monthKey] = (monthlyObservations[monthKey] || 0) + 1;
                    });
        
                    // Sort monthly observations chronologically
                    const sortedMonths = Object.keys(monthlyObservations).sort();
                    const chartData = {
                        labels: sortedMonths,
                        datasets: [{
                            label: `${species.name} Observations`,
                            data: sortedMonths.map(month => monthlyObservations[month]),
                            borderColor: 'rgb(255, 99, 132)',
                            tension: 0.1
                        }]
                    };
        
                    this.speciesTrendChart = new Chart(ctx, {
                        type: 'line',
                        data: chartData,
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: true,
                                    text: `Observation Trend for ${species.name}`
                                }
                            },
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Number of Observations'
                                    }
                                },
                                x: {
                                    title: {
                                        display: true,
                                        text: 'Month'
                                    }
                                }
                            }
                        }
                    });
                }
        
                // Create species map
                const mapElement = document.getElementById('species-map');
                if (mapElement && species.observations.length > 0) {
                    if (this.speciesMap) {
                        this.speciesMap.remove(); // Remove existing map if any
                    }
                    this.speciesMap = L.map('species-map').setView([
                        species.observations[0].LATITUDE, 
                        species.observations[0].LONGITUDE
                    ], 6);

                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '© OpenStreetMap contributors'
                    }).addTo(this.speciesMap);

                    species.observations.forEach(obs => {
                        L.marker([obs.LATITUDE, obs.LONGITUDE])
                        .addTo(this.speciesMap)
                        .bindPopup(`Observed on ${obs.OBSERVATION_DATE.split('T')[0]}`);
                    });
                }
            });
        },
        closeSpeciesModal() {
            this.showSpeciesModal = false;
            // Destroy map and chart if they exist
            if (this.speciesMap) {
                this.speciesMap.remove();
                this.speciesMap = null;
            }
            if (this.speciesTrendChart) {
                this.speciesTrendChart.destroy();
                this.speciesTrendChart = null;
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