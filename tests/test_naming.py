from ducktap.core.naming import (
    cli_command_name,
    env_var_name,
    flag_name,
    kebab_case,
    operation_id_from_path,
    short_name,
    slugify,
    snake_case,
)


def test_slugify():
    assert slugify("Hello World!") == "hello-world"
    assert slugify("My_API v2") == "my-api-v2"


def test_snake_case():
    assert snake_case("listPets") == "list_pets"
    assert snake_case("HTTPServer") == "http_server"
    assert snake_case("kebab-case-name") == "kebab_case_name"


def test_snake_case_sanitizes_non_idents():
    # Real-world operationIds from the GitHub spec
    assert snake_case("meta/root") == "meta_root"
    assert snake_case("repos/get") == "repos_get"
    assert snake_case("apps:list-installations") == "apps_list_installations"
    # Always yields a legal Python identifier
    import keyword
    for raw in ["meta/root", "foo.bar.baz", "weird@thing", "1leadingDigit"]:
        s = snake_case(raw)
        assert s.replace("_", "a").isidentifier() or s.isidentifier()
        assert not keyword.iskeyword(s)


def test_kebab_case():
    assert kebab_case("listPets") == "list-pets"


def test_cli_command_name():
    assert cli_command_name("listPets") == "list-pets"
    assert cli_command_name("getUserById") == "get-user-by-id"


def test_flag_name():
    assert flag_name("petId") == "--pet-id"


def test_env_var_name():
    assert env_var_name("my-api") == "MY_API_API_KEY"


def test_short_name_drops_noise_words():
    assert short_name("Swagger Petstore - OpenAPI 3.0") == "petstore"
    assert short_name("Stripe API") == "stripe"
    assert short_name("GitHub v3 REST API") == "github"
    # Multi-word distinctive titles keep their content (capped at 3 tokens).
    assert short_name("My Multi Word Custom Service") == "my-multi-word"
    # All-noise titles fall back to the full slug rather than empty.
    assert short_name("OpenAPI v3") == "openapi-v3"
    # Empty input returns the explicit fallback.
    assert short_name("") == "api"


def test_operation_id_from_path():
    assert operation_id_from_path("GET", "/pets/{petId}") == "get_pets_pet_id"
    assert operation_id_from_path("POST", "/users") == "post_users"
