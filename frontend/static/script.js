document.addEventListener("DOMContentLoaded", function () {


    const stars = document.querySelectorAll(".star");

    stars.forEach((star) => {

        star.addEventListener("click", function () {

            const rating = this.getAttribute("data-value");
            const courseId = this.getAttribute("data-course");

            fetch("/rate", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    rating: rating,
                    course_id: courseId
                })
            })
            .then(response => response.json())
            .then(data => {
                alert("Rating submitted successfully ⭐");
                location.reload();
            });

        });

    });

    const progressButtons = document.querySelectorAll(".start-course");

    progressButtons.forEach((btn) => {

        btn.addEventListener("click", function () {

            const courseId = this.getAttribute("data-course");

            fetch(`/progress/${courseId}`)
            .then(() => {

                const progressBar = document.querySelector(`#progress-${courseId}`);

                let width = 0;

                const interval = setInterval(() => {

                    if (width >= 100) {

                        clearInterval(interval);

                    } else {

                        width += 10;

                        progressBar.style.width = width + "%";
                        progressBar.innerText = width + "%";

                    }

                }, 200);

            });

        });

    });

    const searchInput = document.getElementById("searchBox");

    if (searchInput) {

        searchInput.addEventListener("keyup", function () {

            const filter = searchInput.value.toLowerCase();

            const courses = document.querySelectorAll(".course-card");

            courses.forEach((course) => {

                const text = course.innerText.toLowerCase();

                if (text.includes(filter)) {

                    course.style.display = "";

                } else {

                    course.style.display = "none";

                }

            });

        });

    }

});