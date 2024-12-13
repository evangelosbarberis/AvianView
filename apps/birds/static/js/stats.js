const app = Vue.createApp({
    data() {
        return {
            searchQuery: '',
            speciesList: [], 
            filteredSpecies: [],
            selectedSpecies: null,
            speciesStatistics: null,
            isLoading: false,
            error: null
        };
    },
    methods: {
        viewSpeciesDetails(species) {
            // Set the search query to the selected species' name
            this.searchQuery = species.COMMON_NAME;
            
            // Fetch statistics for the selected species
            this.fetchSpeciesStatistics(species.COMMON_NAME);
            
            // Set the selected species
            this.selectedSpecies = species;
            
            // Trigger species search to filter the list
            this.fetchSpecies();
        },
        async fetchSpecies() {
            try {
                const response = await axios.get('/birds/search_species', {
                    params: { q: this.searchQuery },
                });
                this.speciesList = response.data.species;
                this.filteredSpecies = this.speciesList;
            } catch (error) {
                console.error('Error fetching species data:', error);
                this.error = 'Failed to fetch species data';
            }
        },
        async fetchSpeciesStatistics(speciesName) {
            this.isLoading = true;
            this.error = null;
            this.speciesStatistics = null;
        
            try {
                const response = await axios.get('/birds/get_species_stats', {
                    params: { species: speciesName }
                });
        
                if (!response.data.error) {
                    this.speciesStatistics = response.data;
                } else {
                    this.error = response.data.error || 'No statistics found for this species';
                }
            } catch (error) {
                console.error('Error fetching species statistics:', error);
                this.error = 'Failed to fetch species statistics';
            } finally {
                this.isLoading = false;
            }
        }
    },
    created() {
        // Fetch all species initially
        this.fetchSpecies();
    },
});

app.mount('#app');