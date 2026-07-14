# CHANGELOG

<!-- version list -->

## v1.0.2 (2026-07-14)


## v1.0.1 (2026-07-14)

### Bug Fixes

- Use re.fullmatch in RegexPattern for full-string matching
  ([`2f491b3`](https://github.com/djachenko/valifold/commit/2f491b3812d7fbfa8fd5c83057b0879d95cfd801))

### Chores

- Apply repokit config updates
  ([`7297e04`](https://github.com/djachenko/valifold/commit/7297e04ea9f21f61cac648c6efe4e01e99d0c53b))


## v1.0.0 (2026-07-07)

### Bug Fixes

- Add build to release extra
  ([`06f72b6`](https://github.com/djachenko/valifold/commit/06f72b69a06cf2cae4c7ae6da89fb0073d72394a))

- Sync version to 0.2.3 matching latest PyPI release
  ([`ae7a274`](https://github.com/djachenko/valifold/commit/ae7a2749c2f3948de2818897a049c21e1dbc5280))

### Chores

- Migrate CI to repokit style
  ([`6f2d013`](https://github.com/djachenko/valifold/commit/6f2d013be6823a50b2b56d336f2da814dd0f4afc))

- Retrigger CI
  ([`77eb94d`](https://github.com/djachenko/valifold/commit/77eb94d65a29a677ff1e94c877e435386cb72db9))


## v0.2.3 (2026-07-07)

### Bug Fixes

- Add -> None return type to all __post_init__ methods
  ([`890f23f`](https://github.com/djachenko/valifold/commit/890f23f4e6138e91232f5a174d5ee72aff3ca673))

- Add py.typed marker and update license to PEP 639 format
  ([`23aa69d`](https://github.com/djachenko/valifold/commit/23aa69d58f3fb37b58f3ebf3cb639097ba7c46a5))

- Enforce mypy strict mode via pyproject.toml
  ([`e0fbd80`](https://github.com/djachenko/valifold/commit/e0fbd802507c56e6a450ffa8db0fc2f9b8c7516b))

- Export public API from valifold.__init__
  ([`b358baa`](https://github.com/djachenko/valifold/commit/b358baa346c27c2e602386ac623069406eec74e5))

- Export public API from valifold.__init__
  ([`333e248`](https://github.com/djachenko/valifold/commit/333e2482567917cf5a1d32664ea99585ebeee8f5))

- Remove license classifier superseded by PEP 639 license expression
  ([`77c79f2`](https://github.com/djachenko/valifold/commit/77c79f2dfb6294ec715f8e66a9811d932bd3d0ce))

- Remove unused imports flagged by ruff
  ([`a465a0c`](https://github.com/djachenko/valifold/commit/a465a0c9ddd442cb823d2379bd79b296328fa3aa))

- Typos in XorValidator error messages
  ([`f744672`](https://github.com/djachenko/valifold/commit/f74467259cedc5c2ec4926da25be4fac875f382b))

- Use {paths} placeholder in MandatoryMissedError message
  ([`280108f`](https://github.com/djachenko/valifold/commit/280108f3b25cd15df1b9461cf060c39bea90096e))

### Chores

- Migrate build backend from setuptools to hatchling
  ([`6cff7be`](https://github.com/djachenko/valifold/commit/6cff7beb87f5b079d614bd3925cee0f5bd5d126d))

### Refactoring

- Move shared fixtures to conftest.py
  ([`b4af7ba`](https://github.com/djachenko/valifold/commit/b4af7ba138cccf022596980873551b1edd235e0e))

- Move shared fixtures to conftest.py
  ([`dcf7fb0`](https://github.com/djachenko/valifold/commit/dcf7fb032ae2eb9366939245b7745e4830fb5aee))

- Rewrite public API tests using project fixtures and parametrize
  ([`6018924`](https://github.com/djachenko/valifold/commit/6018924fda514001a47dd8361cf9a1a9fe7f36d9))

- Rewrite public API tests using project fixtures and parametrize
  ([`1fd9a13`](https://github.com/djachenko/valifold/commit/1fd9a13b848003aa60eed93796ae732463a20a8c))

### Testing

- Add public API integration tests from README examples
  ([`e8a920c`](https://github.com/djachenko/valifold/commit/e8a920ce214c22ecbcf675daff20a19b9d118778))

- Add public API integration tests from README examples
  ([`21676df`](https://github.com/djachenko/valifold/commit/21676df7672724f462613ccc6a739616e4abe151))

- Formatted_message does not raise on real validation errors
  ([`72e5af1`](https://github.com/djachenko/valifold/commit/72e5af1f79f905471d33fa665f8686c20e95f2e4))


## v0.2.2 (2026-03-02)

### Bug Fixes

- Just little formatting
  ([`ce5c2c7`](https://github.com/djachenko/valifold/commit/ce5c2c79fd6f58594650eca763010acfea46841e))

### Features

- Let there be two jobs
  ([`b7fa309`](https://github.com/djachenko/valifold/commit/b7fa309a422e03102ed5462a9c834486ef45c8dd))


## v0.2.1 (2026-03-02)

### Bug Fixes

- Delay for indexing
  ([`e34edae`](https://github.com/djachenko/valifold/commit/e34edae4a65bc7639d356f7c0e8e165be79d2023))


## v0.2.0 (2026-03-01)

### Features

- Enabled release publishing
  ([`0b5df27`](https://github.com/djachenko/valifold/commit/0b5df2796c25de94e88351e7f44070201c7faf81))


## v0.1.2 (2026-03-01)

- Initial Release
