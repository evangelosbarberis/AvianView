const app = Vue.createApp({
    data() {
        return {
            searchQuery: '',
            speciesList: [], 
            filteredSpecies: [],
            selectedSpecies: null,
        };
    },
    methods: {
        viewSpeciesDetails(species) {
            // Fetch additional details for the selected species
            this.selectedSpecies = species;
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
            }
        },
        // countSpeciesObservations(speciesName) {
        //     return this.speciesList.filter(s => 
        //         s.common_name.toLowerCase() === speciesName.toLowerCase()
        //     ).length;
        // }
    },
    created() {
        // Fetch all species initially
        this.fetchSpecies();
    },
});

app.mount('#app');