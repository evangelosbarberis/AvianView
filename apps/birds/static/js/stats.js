const app = Vue.createApp({
    data() {
        return {
            searchQuery: '',
            speciesList: [],
            filteredSpecies: [],
            selectedSpecies: null,
            userBirdStatistics: null,
            isLoading: false,
            error: null,
            activeTab: 'overview'
        };
    },
    computed: {
        sortedSpeciesSummary() {
            return this.userBirdStatistics?.species_summary || [];
        },
        monthlyTrends() {
            return this.userBirdStatistics?.monthly_trends || {};
        }
    },
    methods: {
        async fetchUserBirdStatistics() {
            this.isLoading = true;
            this.error = null;
            
            try {
                const response = await axios.get('/birds/get_user_bird_statistics');
                if (response.data.error) {
                    this.error = response.data.error;
                } else {
                    this.userBirdStatistics = response.data;
                    this.renderMonthlyTrendsChart();
                    this.renderSpeciesDistributionChart();
                }
            } catch (error) {
                console.error('Error fetching bird statistics:', error);
                this.error = 'Failed to fetch bird watching statistics';
            } finally {
                this.isLoading = false;
            }
        },
        viewSpeciesDetails(species) {
            this.selectedSpecies = species;
            this.activeTab = 'species_details';
            this.renderSpeciesLocationMap(species);
        },
        renderMonthlyTrendsChart() {
            const ctx = this.$refs.monthlyTrendsChart;
            if (ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: Object.keys(this.monthlyTrends),
                        datasets: [{
                            label: 'Bird Observations per Month',
                            data: Object.values(this.monthlyTrends),
                            borderColor: 'rgb(75, 192, 192)',
                            tension: 0.1
                        }]
                    }
                });
            }
        },
        renderSpeciesDistributionChart() {
            const ctx = this.$refs.speciesDistributionChart;
            if (ctx) {
                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: this.sortedSpeciesSummary.map(s => s.species),
                        datasets: [{
                            data: this.sortedSpeciesSummary.map(s => s.total_count),
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.6)',
                                'rgba(54, 162, 235, 0.6)',
                                'rgba(255, 206, 86, 0.6)',
                                // Add more colors as needed
                            ]
                        }]
                    }
                });
            }
        },
        renderSpeciesLocationMap(species) {
            const ctx = this.$refs.speciesLocationMap;
            if (ctx) {
                const locationData = this.userBirdStatistics.location_data
                    .find(loc => loc.species === species.species);
                
                if (locationData) {
                    new mapboxgl.Map({
                        container: ctx,
                        style: 'mapbox://styles/mapbox/outdoors-v11',
                        center: [
                            locationData.avg_longitude, 
                            locationData.avg_latitude
                        ],
                        zoom: 6
                    });
                }
            }
        }
    },
    created() {
        this.fetchUserBirdStatistics();
    }
});

// Mount the app after adding components
app.mount('#app');